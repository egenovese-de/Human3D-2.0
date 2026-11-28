# G3 · Decisione d’integrazione

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
