"""Summarize retained G3 runs; per-view observations remain in JSON."""
import json
from pathlib import Path
from statistics import median
import sys


def table(columns, rows):
    return '\n'.join('| '+' | '.join(map(str,row))+' |' for row in [columns,['---']*len(columns),*rows])


def read(path):
    return json.loads(path.read_text())


def report(path,title,body):
    path.write_text(f'# {title}\n\n{body.strip()}\n')


def summarize(rows, field, digits=2):
    values=[r[field] for r in rows if r.get(field) is not None]
    return f'{median(values):.{digits}f}' if values else '—'


def cases(rows, method):
    return [r['fits'][method] for r in rows if r['fits'].get(method,{}).get('status')=='ok']


def main(root, out):
    out.mkdir(parents=True,exist_ok=True)
    subjects = {p.parent.name:read(p) for p in root.glob('A_*/*/registration.json')}
    assert len(subjects)==6
    sectors = read(root/'orientation/orientation.json')
    assert len(sectors)==6
    articulated = [v for p in (root/'articulated').glob('*/registration.json') for v in read(p)['views'].values()]
    assert len(articulated)==6
    views = [v for subject in subjects.values() for v in subject['views'].values()]
    keys=('0','45','90','180','perspective')
    sensors=[]
    for key in keys:
        group=[s['views'][key] for s in subjects.values() if key in s['views']]
        m6=[v['m6_baseline'] for v in group if v.get('m6_baseline',{}).get('status')=='ok']
        rgb=cases(group,'rgb_nominal_shape')
        coarse=[s['orientation_sector'][key] for s in sectors.values() if key in s['orientation_sector']]
        fine=[s['sector_plus_contour'][key] for s in sectors.values() if key in s['sector_plus_contour']]
        sensors.append(dict(view=key,n=len(group),m6=summarize(m6,'anchor_mean_px'),raw=summarize(rgb,'anchor_mean_px'),
                            yaw=summarize(rgb,'yaw_error_deg'),sector=summarize(coarse,'anchor_mean_px'),
                            contour=summarize(fine,'anchor_mean_px'),heldout=summarize(fine,'heldout_mean_px'),
                            iou=summarize(fine,'mask_iou',3),coarse_residual_yaw=summarize(fine,'yaw_error_deg')))
    pose=[]
    for variant in ('near_articulated','far_articulated','cropped_occluded'):
        group=[subject['views'][variant] for subject in subjects.values()]
        for method in ('oracle_camera_all_anchors','oracle_camera_and_fit_pose','oracle_anchors_perspective',
                       'oracle_anchors_weak','oracle_pose_ignored','corrupt_hidden_anchors_trusted'):
            rows=cases(group,method)
            if rows:
                pose.append([variant,method,len(rows),summarize(rows,'anchor_mean_px'),summarize(rows,'heldout_mean_px'),
                             summarize(rows,'mask_iou',3),summarize(rows,'elevation_error_deg'),
                             summarize(rows,'distance_error_percent')])
    camera_table=table(['Vista','N','M6 px','G3 automatico px','Yaw automatico °','Settore px',
                       'Settore + contorno px','Estremità escluse px','IoU dopo contorno'],
                       [[r[k] for k in ('view','n','m6','raw','yaw','sector','contour','heldout','iou')] for r in sensors])
    rgb_count=sum(v['source'] for v in views)
    rear=sensors[3]
    near=next(r for r in pose if r[0]=='near_articulated' and r[1]=='oracle_camera_all_anchors')
    dup=sum(any(row[0]=='duplicate' for row in v['duplicate_case']['suppressed']) for v in sectors.values())
    shifted=sum(any(row[0]=='shifted_copy' for row in v['duplicate_case']['suppressed']) for v in sectors.values())
    perspective=[subject['views']['perspective'] for subject in subjects.values() if 'perspective' in subject['views']]
    full=summarize(cases(perspective,'oracle_anchors_perspective'),'anchor_mean_px')
    weak=summarize(cases(perspective,'oracle_anchors_weak'),'anchor_mean_px')
    report(out/'G3_EXECUTIVE_REPORT.md','Human3D 2.0 · G3 Camera, scala e posa di osservazione',f"""
**Decisione.** La registrazione prospettica e articolata con ancoraggi verificati è riproducibile in laboratorio. L’orientamento automatico ha invertito tutte e sei le viste posteriori. La registrazione da immagini arbitrarie rimane da qualificare.

{camera_table}

Errori mediani di riproiezione su immagini da 384×384. Nelle colonne G3 di questa tabella, polsi e caviglie sono esclusi dal fit. Il percorso M6 usa i punti distali quando disponibili e una forma base diversa. Il settore indicato è un dato esterno noto nel controllo, con intervallo di ±48° attorno a un quadrante.

- **Camera e lateralità.** Per le viste posteriori l’errore scende da **{rear['raw']} px** senza settore a **{rear['sector']} px** con il settore e a **{rear['contour']} px** dopo il raffinamento. Rimangono **{rear['coarse_residual_yaw']}°** di errore mediano di yaw.
- **Posa.** Con camera calibrata e tutti gli ancoraggi esatti il controllo articolato vicino misura **{near[3]} px** e **IoU {near[5]}**. Con pochi punti distali restano errori alle estremità. Gli hash delle anatomie canoniche sono invariati in tutte le serie.
- **Prospettiva.** Nelle due viste prospettiche di G2, usando ancoraggi esatti, la mediana è **{full} px** contro **{weak} px** in debole prospettiva. La scala metrica richiede un riferimento indipendente.
- **Gate aperti.** Orientamento da sole foto, dati reali, auto-occlusione, abbigliamento, prestazioni sul portatile Windows e rebind slim. Nessun VLM utilizzato. G4 rimane separato.

Il [run 46076701570](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46076701570) ha verificato il Lab Runtime e riprodotto i controlli frontale e articolato vicino sul commit del motore `e348408`. La matrice estesa è stata eseguita localmente su Linux CPU.
""")
    articulated_rgb=cases(articulated,'rgb_nominal_shape')
    report(out/'G3_REGISTRATION_BENCHMARK.md','G3 · Protocollo e misure',f"""
## Dataset e metodi

{rgb_count} viste RGB recuperate da G2, {len(views)-rgb_count} controlli con articolazione nota e {len(articulated)} nuove immagini Blender articolate. Sei geometrie MakeHuman, M6 fissato a `e0ae4ea`. Il percorso RGB usa esclusivamente MediaPipe e anatomia nominale predefinita. Le varianti “known shape” e “oracle” sono esplicite nei dati. Non sono stati ammessi scatti e scansioni reali.

La camera stima yaw, elevazione, roll, scala relativa, distanza lungo l’asse ottico e offset sul piano immagine. I parametri di posa comprendono due rotazioni per ciascuno degli otto segmenti di braccia e gambe. Le ipotesi di lato e orientamento sono confrontate con il residuo robusto agli ancoraggi e una silhouette locale. Il raffinamento successivo prova piccoli aggiustamenti alla camera con posa congelata. Le pose del torso, le dita e la torsione articolare completa rimangono fuori da questo studio.

## Riproduzione per camera e posa

{camera_table}

{table(['Condizione','Variante','N','Ancoraggi px','Estremità px','IoU','Elevazione °','Distanza %'],pose)}

L’errore mediano del fit nominale RGB nelle nuove viste articolate è **{summarize(articulated_rgb,'anchor_mean_px')} px**. Nel controllo oracle con tutti gli ancoraggi, i valori alle estremità includono punti usati in stima. Gli altri fit escludono polsi e caviglie dalla stima. Il report JSON include i casi con troppo pochi punti: l’astensione è parte del risultato.

## Visibilità, incertezza e runtime

I controlli annotati usano quattro stati, tra cui pixel ignoto e bordo incerto. Le maschere RGB escludono un bordo incerto, mentre l’attribuzione automatica di auto-occlusioni e vestiti non è qualificata. Il filtro ha riconosciuto {dup}/6 copie esatte e {shifted}/6 copie traslate di un pixel. La vista complementare resta disponibile.

La covarianza per camera è locale, condizionata ai prior e propaga l’errore pixel per ancoraggio. Conserva sia le ipotesi di lateralità sia il rango numerico dei dati. Non misura la probabilità di una soluzione globale, come mostra il caso posteriore. La focale EXIF equivalente è un prior approssimato. Distanza e scala fisiche restano ambigue in assenza di metadati o misure compatibili.

Il fit RGB nominale sulle viste G2 ha mediana **{summarize(cases([v for v in views if v['source']],'rgb_nominal_shape'),'seconds')} s** per vista su Linux CPU, senza includere il detector o Blender. Cinque test di contratto G3 e 91 regressioni M6 passate. La prova Linux di CI usa il Lab Runtime verificato. Il portatile Windows di riferimento non era disponibile.
""")
    report(out/'G3_ARCHITECTURE_DECISION.md','G3 · Decisione d’integrazione',"""
| Meccanismo | Decisione | Condizione |
| --- | --- | --- |
| Coordinate pixel-centre, EXIF 1–8 e trasformazioni della foto | Adottare | Memorizzare il frame grezzo e quello orientato. Tracciare composizione crop e resize. |
| Prospettiva e prior focale | Adottare con limiti | Calibrare quando possibile. Distorsione ottica e distinzione di punto principale e traslazione laterale rimangono aperte. |
| Debole prospettiva | Opzionale | Usare come candidato nelle viste lontane e misurarne l’errore. |
| Settore esterno e ipotesi rivali di lateralità | Adottare con limiti | Conservare il settore noto e la provenienza. Una vista senza orientamento affidabile conserva più ipotesi. |
| Orientamento automatico | Rinviare | Le viste posteriori dimostrano che la silhouette e la confidenza MediaPipe sono insufficienti. |
| Contorno e posa di osservazione | Adottare con limiti | Affinare localmente dopo la registrazione. Conservare le regioni ignote. Priori e scarsa osservabilità limitano i segmenti distali. |
| Scala fisica e visibilità | Condizionali | Misura indipendente per la scala. Occlusione con provenienza esplicita. |
| Soppressione dei duplicati | Opzionale | Copie esatte coperte. Risolvere lievi disallineamenti prima di attenuare foto quasi duplicate. |

Il contratto per il fitter prevede camera, posa di osservazione, stato della scala, visibilità per regione, covarianza locale e ipotesi rivali. La forma canonica resta immutabile durante la registrazione e la posa finale è un passaggio distinto. Per l’adozione, aggiungere casi posteriori reali, rebind sul profilo slim e misure hardware di destinazione. Stima indicativa di 5–9 giornate ingegnere per integrare il sottoinsieme qualificato, esclusi acquisizione di dati reali e test Windows.
""")
    backlog=[
        ('001','Handoff e riproducibilità','DONE'),('002','EXIF, crop e pixel-centre','DONE'),
        ('003','Gauge di scala e focale','DONE'),('004','Modello prospettico e debole','DONE'),
        ('005','Orientamento automatico posteriore','PARTIAL'),('006','Posa e ancoraggi distali','DONE'),
        ('007','Validazione della covarianza','PARTIAL'),('008','Auto-occlusione e indumenti','PARTIAL'),
        ('009','Duplicati con disallineamento','PARTIAL'),('010','Rebind slim','PARTIAL'),
        ('011','CPU Windows e scatti reali','PARTIAL'),('012','Render, misure e scene Blender','DONE'),
        ('013','Decisione tecnica','DONE'),
    ]
    report(out/'BACKLOG_G3.md','G3 · Backlog',table(['ID','Attività','Stato'],[['G3-'+k,a,b] for k,a,b in backlog]))
    (out/'G3_METRICS.json').write_text(json.dumps(dict(subjects=len(subjects),rgb_views=rgb_count,
        articulated_controls=len(views)-rgb_count,articulated_rgb=len(articulated),camera=sensors,pose=pose),
        indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))
