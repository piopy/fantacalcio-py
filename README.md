# Fantacalcio-PY

Fantacalcio-PY è un tool che aiuta gli utenti a prepararsi per l'asta del fantacalcio. Il programma esegue le seguenti operazioni:

1.  **Recupero Dati**: Scarica i dati dei calciatori da due fonti:
    *   **FPEDIA**: per le statistiche della stagione in corso.
    *   **FSTATS**: per le statistiche della stagione precedente.
2.  **Elaborazione e Unione**: Pulisce, elabora e unisce i dati provenienti dalle diverse fonti in un unico dataset.
3.  **Calcolo Indice di Convenienza**: Calcola un indice di "convenienza" per ogni giocatore. Questo indice mette in rapporto il valore di un giocatore (prezzo base all'asta) con il suo rendimento passato e attuale, aiutando a identificare giocatori sottovalutati.
4.  **Salvataggio Risultati**: I risultati finali, ordinati per indice di convenienza, vengono salvati in un file Excel.

## Disclaimer

- Se perdete il fanta non è colpa mia, io ci so arrivato secondo co sta roba. E l'anno dopo primo.
- Il tool utilizza i csv prodotti da fpedia, tutti i dati processati sono loro, dato che fantagazzetta ha deciso di tagliare i dataset open.

*Refactor del codice di cttynul*

## Prerequisiti

Per utilizzare questo progetto, è necessario avere installato **Python 3.10** o superiore e **Poetry** per la gestione delle dipendenze.

## Installazione

1.  **Clonare la repository (se non già fatto)**:
    ```bash
    git clone <url_della_repository>
    cd fantacalcio-py-main
    ```

2.  **Installare le dipendenze**:
    Questo progetto utilizza `poetry` per gestire le dipendenze. Per installarle, eseguire il seguente comando dalla root del progetto:
    ```bash
    poetry install
    ```
    Questo comando creerà un ambiente virtuale e installerà tutte le librerie necessarie specificate nel file `pyproject.toml`.

## Configurazione

Il progetto richiede delle credenziali per accedere a `FSTATS`. Queste credenziali vanno inserite in un file `.env` nella root del progetto.

Il file `config.py` contiene altre configurazioni, come gli URL per lo scraping e i percorsi dei file di output. Non dovrebbe essere necessario modificarlo per il funzionamento base.

## Avvio del Progetto

Per avviare l'analisi completa, eseguire lo script `main.py` utilizzando `poetry`.

```bash
poetry run python main.py
```

Lo script eseguirà tutti i passaggi (recupero, elaborazione, calcolo e salvataggio).

## Output

Al termine dell'esecuzione, verranno creati dei file Excel nella directory `data/output`. 

## WIP

- [ ] Messa a punto del calcolo dell'indice di convenienza
- [ ] Formazione consigliata
- [ ] Frontend

## Stars

[![Star History Chart](https://api.star-history.com/svg?repos=piopy/fantacalcio-py&type=Date)](https://www.star-history.com/#piopy/fantacalcio-py&Date)
