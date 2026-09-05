# AGENTS.md — fantacalcio-py

## Entry
- Nuovo main: `pipeline.py` (asta: Punteggio_Asta_100, prezzi, Tier, Hidden Gem).
- Libreria: `src/` (`config`, `fpd`, `providers`, `merge`, `scoring`, `utils`).
- `cli.py` = legacy congelata, già non importabile (puntava a moduli FSTATS cancellati). Non fixare: verrà sostituita da TUI.

## Run (uv, non poetry)
README cita ancora poetry ma l'env attivo è uv (`.venv`, `uv.lock`):
```bash
uv run pipeline.py --anno 2026 --partecipanti 10 --crediti 500
uv run pipeline.py --no-ext   # senza provider esterno
uv run pipeline.py --force    # re-scrape FPD (~76s)
```
- Deps da `[project]` in `pyproject.toml` (`uv sync` basta; `[tool.uv] package=false` perché non è un package installabile). Sezione `[tool.poetry]` legacy, ignorarla.
- Import interni sempre come package: `from src.xxx import ...`, mai `import config` root-style.

## Env e cache
- `.env` richiesto: `FSTATS_MAIL` + `FSTATS_PASSWORD` (nome legacy: autenticano FantaGOAT, non FSTATS).
- Cache in `data/`: `_giocatori.csv`, `giocatori_urls.txt`, `understat_<anno>.json`, `provider_ext.json`. Run riusa cache se presente.
- Output: `data/output/fantacalcio_asta_<anno>_<anno+1>_<p>p_<cr>cr.xlsx` + stesso nome `.json` (sidecar per frontend: envelope `{meta, players, rose}`, no colonna Tier).
- Colonne annate dinamiche da `--anno`: `Gol 25-26` = prev, `Gol 26-27` = curr. Mai hardcodare anni.
- Frontend asta offline: `docs/` (statico, no build, no deps; in `docs/` perché è sorgente GitHub Pages). Stato in localStorage + export/import JSON.

## Workflow
- Mai commit/push senza ordine esplicito dell'utente.
- No test, no CI, no lint enforced. Verifica = `uv run pipeline.py --help` + run cached (output atteso: `OK ...xlsx — N gioc, M gem`).
