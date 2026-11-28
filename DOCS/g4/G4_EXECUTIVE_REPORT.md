# Human3D 2.0 · G4 Fitting anatomico canonico

**Decisione.** G4 è un candidato per acquisizioni con camere calibrate. Il passaggio a foto arbitrarie resta bloccato dalla registrazione di camera. La validazione anatomica non può essere sostituita da una buona sovrapposizione della sagoma.

| Cohort | G2 E1 | G4 con maschere M6 | G4 con maschere RGB |
| --- | --- | --- | --- |
| MakeHuman, 6 | 5.66 | 3.22 | 4.02 |
| MB-Lab, 4 | 20.09 | 21.10 | 21.06 |

Distanza media simmetrica dalla superficie di riferimento in millimetri. G2 E1 e G4 M6 usano le stesse maschere M6 e camere calibrate. Cambiano il criterio di errore e la strategia di ottimizzazione. I numeri MB-Lab provengono da quattro mesh con topologia indipendente della stessa libreria. G4 non migliora questa coorte in media.

- **Camera.** Con le camere G3 stimate, il caso muscolare misura **81.61 mm**, contro **2.71 mm** a camera calibrata e con la stessa maschera RGB. La sola sostituzione di inquadratura, traslazione immagine e scala riproduce **81.54 mm**, mentre la sola sostituzione dello yaw misura **3.44 mm**.
- **Profilo slim.** La ricerca verso il candidato rifiutato, vincolata al validatore M6, migliora la prova RGB da **25.09 mm** a **4.73 mm**. Il candidato migliore che violava il controllo resta escluso.
- **Posa e invarianza.** Due prove con viste articolate separano gli errori di posa da quelli anatomici. Il cambio della vista target nel CLI e le prove con riordino, copia esatta e vista irrisolta hanno preservato l’hash canonico.
- **Raccomandazione.** Usare maschere M6 e camere calibrate, mantenere immutabile la geometria canonica durante la registrazione e bloccare il controllo di statura senza una scala indipendente. Il blocco della statura non corregge da solo l’errore di inquadratura.

Il lavoro rimane sperimentale sul [branch G4](https://github.com/egenovese-de/Human3D-2.0/tree/lab/g4-anatomical-fitting). La prova non include scatti reali né il portatile Windows di riferimento.
