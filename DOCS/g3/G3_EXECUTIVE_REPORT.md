# Human3D 2.0 · G3 Camera, scala e posa di osservazione

**Decisione.** La registrazione prospettica e articolata con ancoraggi verificati è riproducibile in laboratorio. L’orientamento automatico ha invertito tutte e sei le viste posteriori. La registrazione da immagini arbitrarie rimane da qualificare.

| Vista | N | M6 px | G3 automatico px | Yaw automatico ° | Settore px | Settore + contorno px | Estremità escluse px | IoU dopo contorno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 6 | 12.99 | 5.76 | 27.42 | 6.40 | 5.79 | 8.62 | 0.744 |
| 45 | 6 | 9.91 | 5.14 | 6.68 | 5.29 | 4.76 | 3.44 | 0.804 |
| 90 | 6 | 7.09 | 7.41 | 0.82 | 7.13 | 7.00 | 10.46 | 0.752 |
| 180 | 6 | 9.21 | 81.38 | 158.01 | 5.34 | 4.33 | 5.48 | 0.801 |
| perspective | 2 | 8.43 | 6.32 | 8.82 | — | — | — | — |

Errori mediani di riproiezione su immagini da 384×384. Nelle colonne G3 di questa tabella, polsi e caviglie sono esclusi dal fit. Il percorso M6 usa i punti distali quando disponibili e una forma base diversa. Il settore indicato è un dato esterno noto nel controllo, con intervallo di ±48° attorno a un quadrante.

- **Camera e lateralità.** Per le viste posteriori l’errore scende da **81.38 px** senza settore a **5.34 px** con il settore e a **4.33 px** dopo il raffinamento. Rimangono **21.01°** di errore mediano di yaw.
- **Posa.** Con camera calibrata e tutti gli ancoraggi esatti il controllo articolato vicino misura **0.53 px** e **IoU 0.965**. Con pochi punti distali restano errori alle estremità. Gli hash delle anatomie canoniche sono invariati in tutte le serie.
- **Prospettiva.** Nelle due viste prospettiche di G2, usando ancoraggi esatti, la mediana è **0.55 px** contro **1.91 px** in debole prospettiva. La scala metrica richiede un riferimento indipendente.
- **Gate aperti.** Orientamento da sole foto, dati reali, auto-occlusione, abbigliamento, prestazioni sul portatile Windows e rebind slim. Nessun VLM utilizzato. G4 rimane separato.

Il [run 46076701570](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46076701570) ha verificato il Lab Runtime e riprodotto i controlli frontale e articolato vicino sul commit del motore `e348408`. La matrice estesa è stata eseguita localmente su Linux CPU.
