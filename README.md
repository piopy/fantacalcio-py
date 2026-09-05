# Fantacalcio-PY

Fantacalcio-PY è un tool che aiuta gli utenti a prepararsi per l'asta del fantacalcio. Il programma esegue le seguenti operazioni:

1.  **Recupero Dati**: Scarica i dati dei calciatori da:
    *   **FPD**: per anagrafiche, ruoli, skills.
    *   **Understat**: per xG/xA e stats stagione prev/corr (sostituisce FSTATS, non più funzionante).
2.  **Elaborazione e Unione**: Pulisce, elabora e unisce i dati provenienti dalle diverse fonti in un unico dataset.
3.  **Calcolo Indice di Convenienza**: Calcola un indice di "convenienza" per ogni giocatore. Questo indice mette in rapporto il valore di un giocatore (prezzo base all'asta) con il suo rendimento passato e attuale, aiutando a identificare giocatori sottovalutati.
4.  **Salvataggio Risultati**: I risultati finali, ordinati per indice di convenienza, vengono salvati in un file Excel.

## Disclaimer

- Se perdete il fanta non è colpa mia, io ci so arrivato secondo co sta roba. E l'anno dopo primo.
- Il tool utilizza i csv prodotti da fpd, tutti i dati processati sono loro, dato che fantagazzetta ha deciso di tagliare i dataset open.

*Refactor del codice di cttynul*

## [Cliccare qui per il README della CLI](README_CLI.md)

## Prerequisiti

Python 3.10+ e [uv](https://docs.astral.sh/uv/). (Il `pyproject.toml` è ancora in formato poetry: `uv` lo legge per le dipendenze, ma i comandi sotto usano `uv`, non `poetry`.)

## Installazione

1.  **Clonare la repository (se non già fatto)**:
    ```bash
    git clone <url_della_repository>
    cd fantacalcio-py
    ```

2.  **Installare le dipendenze**:
    ```bash
    uv sync
    ```
    Se un pacchetto manca al run: `uv pip install <pkg>` e rilancia.

## Configurazione

Crea un file `.env` nella root con le credenziali provider esterno (nome legacy: autenticano FantaGOAT, non FSTATS):

```bash
FSTATS_MAIL=tuamail@example.com
FSTATS_PASSWORD=tupassword
```

Senza `.env` (o con `--no-ext`) la pipeline gira comunque, senza indice esterno/titolarità/rose.

`src/config.py` contiene URL e percorsi. Non serve modificarlo per l'uso base.

## Avvio

Entrypoint: `pipeline.py` (punteggio asta /100, prezzi per crediti, Hidden Gem, alternative).

```bash
uv run pipeline.py --anno 2026 --partecipanti 10 --crediti 500
uv run pipeline.py --no-ext    # senza provider esterno
uv run pipeline.py --force     # re-scrape FPD (~60s)
```

## Output

In `data/output/`:
- `fantacalcio_asta_<anno>_<anno+1>_<p>p_<cr>cr.xlsx` — Masterlist + Hidden_Gems + fogli per ruolo + Per_Squadra
- stesso nome `.json` — stesse righe, per il frontend
- `rose_<anno>_<anno+1>.json` — modulo, formazione, rigoristi per squadra di Serie A

Colonne annate dinamiche da `--anno`: `Gol 25-26` = stagione scorsa, `Gol 26-27` = live.

## Frontend asta (offline)

Apri `src/frontend/index.html` nel browser, carica il `.json` (e il `rose_*.json` per la tab Serie A).
Listone filtrabile/ordinabile, assegnazioni con budget per squadra, stelline, lista spesa con note, tab Infortunati.

Legacy congelata: `cli.py` (verrà sostituita da TUI).

## WIP

- [ ] Messa a punto del calcolo dell'indice di convenienza
- [ ] Formazione consigliata (post-asta, da tab Asta)
- [x] Frontend (`src/frontend/`)

## Special thanks!
- [AndreaBozzo](https://github.com/AndreaBozzo/) per aver creato [la CLI figa](https://github.com/AndreaBozzo/fantacalcio-py)
- [informagico](https://github.com/informagico/) per aver creato [un frontend comprensibile anche a chi non sa cosa sia un excel](https://github.com/informagico/fantavibe) 



## Stars

[![Star History Chart](https://api.star-history.com/svg?repos=piopy/fantacalcio-py&type=Date)](https://www.star-history.com/#piopy/fantacalcio-py&Date)
