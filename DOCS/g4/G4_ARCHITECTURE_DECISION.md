# G4 · Decisione d’integrazione

| Meccanismo | Decisione | Condizione |
| --- | --- | --- |
| Fitter G1 nativo con un solo vettore canonico | Adottare con limiti | Introdurre inizialmente su acquisizioni calibrate. I parametri mantengono i limiti G1 e ogni risultato supera il controllo M6. |
| Maschere M6 e contorno simmetrico con gap | Adottare con limiti | Usare confidenza, mascheramento locale e attenuazione per incertezza di registrazione. Confrontare diagnostica IoU e residui indipendenti. |
| Posa per vista | Adottare con limiti | Conservare trasformazioni separate, applicate dopo aver valutato il vettore canonico. Prima qualificare la stima delle estremità. |
| Inquadratura, scala e posa G3 non calibrata | Rinviare | Separare la stima della camera dal prior anatomico e imporre un riferimento metrico quando richiesto. Richiedere conformità per vista prima della migrazione. |
| Ricerca sotto guard di rebind | Adottare | Mantenere intatta la soglia M6. Conservare gli scarti in diagnostica. |
| Abbigliamento e silhouette parziali | Condizionale | Le annotazioni attendibili limitano la geometria dall’esterno. Le regioni non osservate non entrano nell’uguaglianza del contorno. L’estrazione automatica resta aperta. |
| Uso esteso al pubblico | Rinviare | Servono foto reali con calibrazione nota in un primo controllo, famiglie indipendenti aggiuntive e prestazioni verificate su Windows. |

Il confine di integrazione è un manifest di viste registrate, con provenienza della camera e della scala più una mappa di evidenza locale. Il CLI produce geometria canonica ripetibile, parametri, pesi e astensioni. Non è prevista un’integrazione GUI in questa fase. Il confronto Blender conserva UV e corrispondenza di topologia sulle forme MakeHuman. La scena resta uno strumento di confronto geometrico.
