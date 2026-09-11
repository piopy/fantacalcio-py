# old_version — foto congelata del branch `main`

Vecchia pipeline flat (`main.py` + `data_retriever.py`, `data_processor.py`,
`fuzzy_matcher.py`, `convenienza_calculator.py`, `config.py`), estratta da `main`
via `git archive`. Solo retrocompatibilità, non sviluppare qui.

## Quando usarla

Se avevi costruito qualcosa sul vecchio formato output e la nuova pipeline
(`pipeline.py` + `src/`) ti rompe tutto, usa questa.

## Differenze formato output che rompono compatibilità

| Vecchio (`main.py`) | Nuovo (`pipeline.py`) |
|---|---|
| JSON envelope `{metadata, players}` (`metadata`: source, total_players, generated_at, columns) | envelope `{meta, players, rose}` |
| Colonne `Convenienza`, `Convenienza Potenziale` | `Affare FPY` (0–100), `Score FPY` (1–99), `Hidden Gem?`, `Alternative Affini` |
| Prezzi interni only | `Prezzo_<crediti>` + `Fonte Value` (`listone`/`interno` con `--listone`) |
| Anni hardcoded (2024/2025) | colonne annate dinamiche da `--anno` |
| Poetry | `uv` (`uv sync`, `uv run`) |

## Run vecchio stile

```bash
cd old_version
poetry install  # o pip sui requisiti di allora
python main.py
```

Output in `../data/output/` (stesse path `config.py`: `data/output/`).
Non committare output: `data/` è gitignored.
