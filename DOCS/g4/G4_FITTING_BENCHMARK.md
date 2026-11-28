# G4 · Protocollo e risultati

## Anatomia canonica

| Caso | G2_E1 | G2_rgb_gap | G4_RGB_IOU | G4_RGB | G4_M6 | G4_ORACLE | G4_G3_SECTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | 6.57 | 5.09 | 5.34 | 4.30 | 3.28 | 2.93 | 33.60 |
| A_heldout_1 | 5.59 | 5.99 | 5.41 | 5.54 | 5.65 | 4.45 | 10.11 |
| A_heldout_2 | 9.05 | 8.62 | 3.20 | 3.53 | 2.65 | 2.50 | 18.29 |
| A_high_mass | 2.19 | 3.05 | 3.17 | 3.32 | 2.72 | 2.56 | 11.31 |
| A_muscular | 4.68 | 4.98 | 2.69 | 2.71 | 2.31 | 2.05 | 81.61 |
| A_slim | 5.89 | 4.95 | 3.66 | 4.73 | 2.75 | 2.66 | 24.27 |
| B_female | 20.97 | 22.26 | 22.72 | 22.89 | 22.83 | 23.22 | — |
| B_female_expanded | 21.33 | 21.46 | 22.16 | 22.30 | 21.93 | 21.59 | — |
| B_male | 19.15 | 19.56 | 19.20 | 19.52 | 19.59 | 19.62 | — |
| B_male_expanded | 18.89 | 19.90 | 18.69 | 19.52 | 20.04 | 19.61 | — |

Valori di distanza simmetrica dalla superficie in mm, senza riallineamento candidato per candidato. Stessa misura G2 con 12.000 campioni per direzione sui triangoli Blender e semi 818/819. `G4_RGB_IOU` e `G4_RGB` usano stessa famiglia di maschere RGB calibrate e stesso budget. Il primo usa IoU e il secondo combina distanza di contorno troncata, occupazione e gap, con aggregazione robusta. `G4_ORACLE` usa maschere di riferimento. `G4_G3_SECTOR` usa camere con settore esterno, posa canonica nota in questa ablation e statura sbloccata come stress esplicito. I casi B non hanno camere G3 ammesse. I B sono stati nuovamente renderizzati e segmentati con Blender 4.3.2 e pose model M6. Un risultato B non equivale a validazione su persone reali.

## Camera e scala

| Caso | CAMERA_YAW_ONLY | CAMERA_FRAME_ONLY | G4_G3_RELATIVE |
| --- | --- | --- | --- |
| A_adult_asymmetric | 5.35 | 36.34 | 31.50 |
| A_heldout_1 | 6.77 | 10.25 | 9.39 |
| A_heldout_2 | 3.75 | 18.57 | 18.65 |
| A_high_mass | 5.41 | 8.82 | 11.96 |
| A_muscular | 3.44 | 81.54 | 81.32 |
| A_slim | 25.09 | 20.61 | 24.28 |

Yaw e parametri di inquadratura sono sostituiti separatamente, con le restanti componenti della camera calibrata fissate. Il test relativo usa la camera G3, blocca Height al valore di prior, e non dichiara una misura fisica. Il fattore dominante sui casi peggiori è la combinazione di scala e offset nella camera G3 stimata contro la geometria nominale. La statura bloccata da sola non risolve il bias. I controlli camera usano un budget di 500 chiamate contro 670 della matrice principale.

## Posa nelle proiezioni

| Caso | MIXED_ORACLE_POSE | MIXED_POSE_IGNORED | MIXED_G3_POSE |
| --- | --- | --- | --- |
| A_heldout_1 | 4.82 | 4.62 | 4.73 |
| A_high_mass | 2.37 | 3.04 | 3.52 |

Le due serie usano due viste RGB neutre calibrate più tre osservazioni articolate. La componente occlusa ha un’annotazione sperimentale separata. La stima G3 usa il settore e la focale controllati per il confronto. Le deformazioni sono applicate alla mesh candidata durante la proiezione e il risultato salvato è il vettore canonico. Più viste con posa stimata non migliorano automaticamente la ricostruzione. I raw JSON conservano tempi, esclusioni, pesi, superfici per banda e scarti di sezione. Per i fit G4 M6 di A la mediana del solo fitting è **7.34 s** sul runner locale Linux, esclusi estrazione, registrazione e render; cinque contratti G4 e 91 regressioni M6 passati.

## Struttura e provenienza

Il caso slim respinge i checkpoint che alterano l’area dei triangoli oltre il limite di M6. G4 interpola nello spazio dei parametri dal checkpoint valido verso il candidato respinto e promuove solamente stati verificati che migliorano l’obiettivo. L’output più vicino non è una dimostrazione che il rebind della geometria slim originale sia corretto. Le forme G4 con maschere M6 hanno tutte superato il validatore. Il CLI ha prodotto l’hash canonico `54c24a36ca695af08ec26d14702ddcedea961461acf6aa16c792e453e83387e6` con entrambe le viste target.
