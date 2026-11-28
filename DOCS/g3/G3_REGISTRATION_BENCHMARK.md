# G3 · Protocollo e misure

## Dataset e metodi

26 viste RGB recuperate da G2, 18 controlli con articolazione nota e 6 nuove immagini Blender articolate. Sei geometrie MakeHuman, M6 fissato a `e0ae4ea`. Il percorso RGB usa esclusivamente MediaPipe e anatomia nominale predefinita. Le varianti “known shape” e “oracle” sono esplicite nei dati. Non sono stati ammessi scatti e scansioni reali.

La camera stima yaw, elevazione, roll, scala relativa, distanza lungo l’asse ottico e offset sul piano immagine. I parametri di posa comprendono due rotazioni per ciascuno degli otto segmenti di braccia e gambe. Le ipotesi di lato e orientamento sono confrontate con il residuo robusto agli ancoraggi e una silhouette locale. Il raffinamento successivo prova piccoli aggiustamenti alla camera con posa congelata. Le pose del torso, le dita e la torsione articolare completa rimangono fuori da questo studio.

## Riproduzione per camera e posa

| Vista | N | M6 px | G3 automatico px | Yaw automatico ° | Settore px | Settore + contorno px | Estremità escluse px | IoU dopo contorno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 6 | 12.99 | 5.76 | 27.42 | 6.40 | 5.79 | 8.62 | 0.744 |
| 45 | 6 | 9.91 | 5.14 | 6.68 | 5.29 | 4.76 | 3.44 | 0.804 |
| 90 | 6 | 7.09 | 7.41 | 0.82 | 7.13 | 7.00 | 10.46 | 0.752 |
| 180 | 6 | 9.21 | 81.38 | 158.01 | 5.34 | 4.33 | 5.48 | 0.801 |
| perspective | 2 | 8.43 | 6.32 | 8.82 | — | — | — | — |

| Condizione | Variante | N | Ancoraggi px | Estremità px | IoU | Elevazione ° | Distanza % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| near_articulated | oracle_camera_all_anchors | 6 | 0.53 | 0.45 | 0.965 | 0.00 | 0.00 |
| near_articulated | oracle_camera_and_fit_pose | 6 | 6.38 | 18.59 | 0.689 | 0.00 | 0.00 |
| near_articulated | oracle_anchors_perspective | 6 | 6.57 | 18.61 | 0.682 | 1.93 | 0.33 |
| near_articulated | oracle_anchors_weak | 6 | 6.57 | 17.96 | 0.667 | 6.98 | — |
| near_articulated | oracle_pose_ignored | 6 | 8.97 | 14.73 | 0.654 | 3.27 | 0.19 |
| far_articulated | oracle_camera_all_anchors | 6 | 0.37 | 0.29 | 0.972 | 0.00 | 0.00 |
| far_articulated | oracle_camera_and_fit_pose | 6 | 3.53 | 10.18 | 0.796 | 0.00 | 0.00 |
| far_articulated | oracle_anchors_perspective | 6 | 3.66 | 10.29 | 0.790 | 0.10 | 0.21 |
| far_articulated | oracle_anchors_weak | 6 | 3.80 | 10.21 | 0.780 | 2.41 | — |
| far_articulated | oracle_pose_ignored | 6 | 8.03 | 13.45 | 0.768 | 0.63 | 2.63 |
| cropped_occluded | oracle_camera_all_anchors | 6 | 4.01 | 9.29 | 0.822 | 0.00 | 0.00 |
| cropped_occluded | oracle_camera_and_fit_pose | 5 | 6.76 | 18.56 | 0.743 | 0.00 | 0.00 |
| cropped_occluded | oracle_anchors_perspective | 5 | 9.35 | 22.88 | 0.644 | 6.75 | 2.58 |
| cropped_occluded | oracle_anchors_weak | 5 | 8.02 | 20.47 | 0.717 | 10.98 | — |
| cropped_occluded | oracle_pose_ignored | 5 | 8.98 | 11.56 | 0.685 | 26.12 | 4.94 |
| cropped_occluded | corrupt_hidden_anchors_trusted | 6 | 23.70 | 38.72 | 0.339 | 46.17 | 22.94 |

L’errore mediano del fit nominale RGB nelle nuove viste articolate è **10.41 px**. Nel controllo oracle con tutti gli ancoraggi, i valori alle estremità includono punti usati in stima. Gli altri fit escludono polsi e caviglie dalla stima. Il report JSON include i casi con troppo pochi punti: l’astensione è parte del risultato.

## Visibilità, incertezza e runtime

I controlli annotati usano quattro stati, tra cui pixel ignoto e bordo incerto. Le maschere RGB escludono un bordo incerto, mentre l’attribuzione automatica di auto-occlusioni e vestiti non è qualificata. Il filtro ha riconosciuto 6/6 copie esatte e 0/6 copie traslate di un pixel. La vista complementare resta disponibile.

La covarianza per camera è locale, condizionata ai prior e propaga l’errore pixel per ancoraggio. Conserva sia le ipotesi di lateralità sia il rango numerico dei dati. Non misura la probabilità di una soluzione globale, come mostra il caso posteriore. La focale EXIF equivalente è un prior approssimato. Distanza e scala fisiche restano ambigue in assenza di metadati o misure compatibili.

Il fit RGB nominale sulle viste G2 ha mediana **1.70 s** per vista su Linux CPU, senza includere il detector o Blender. Cinque test di contratto G3 e 91 regressioni M6 passate. La prova Linux di CI usa il Lab Runtime verificato. Il portatile Windows di riferimento non era disponibile.
