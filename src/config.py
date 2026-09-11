# config.py — costanti nuovo main (pipeline.py + src/). cli.py legacy congelata.
import os
import base64


def decode(stringa):
    return base64.b64decode(stringa).decode("utf-8")


# Percorsi dei file
DATA_DIR = "data"
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
GIOCATORI_URLS_FILE = os.path.join(DATA_DIR, "giocatori_urls.txt")
GIOCATORI_CSV = os.path.join(DATA_DIR, "_giocatori.csv")

# URLS — unico punto di raccolta. Sorgenti offuscate: solo base64 qui,
# mai URL in chiaro nel resto del codice.
BASEURL_FPD = decode("aHR0cHM6Ly93d3cuZmFudGFjYWxjaW9wZWRpYS5jb20=")
FPD_URL = f"{BASEURL_FPD}/lista-calciatori-serie-a/"
EXT_LOGIN_URL = decode("aHR0cHM6Ly9oM3BweGlycXNnLmV4ZWN1dGUtYXBpLnVzLWVhc3QtMi5hbWF6b25hd3MuY29tL3Byb2QvYXV0aC9lbWFpbC9sb2dpbg==")
EXT_ORIGIN = decode("aHR0cHM6Ly9hcHAuZmFudGFnb2F0Lml0Lw==")
EXT_CLIENT_ID = decode("ZmFudGFnb2F0LWFwcA==")
EXT_API_HOST = decode("YXBpLmZhbnRhZ29hdC5pdA==")
EXT_PLAYERS_URL = decode("aHR0cHM6Ly9hcGkuZmFudGFnb2F0Lml0L3YxL3BsYXllcnM=")
EXT_STANDINGS_URL = decode("aHR0cHM6Ly9hcGkuZmFudGFnb2F0Lml0L3YxL3N0YW5kaW5ncw==")
STATS_LEAGUE_URL = decode("aHR0cHM6Ly91bmRlcnN0YXQuY29tL2xlYWd1ZS9TZXJpZV9BLw==")
STATS_PLAYERS_URL = decode("aHR0cHM6Ly91bmRlcnN0YXQuY29tL21haW4vZ2V0UGxheWVyc1N0YXRzLw==")
INF_URL = decode("aHR0cHM6Ly93d3cuZmFudGFjYWxjaW9wZWRpYS5jb20vYXJ0aWNvbGktZmNwL2NvbnNpZ2xpLWZhbnRhY2FsY2lvLzc1LWxpc3RhLWluZm9ydHVuYXRpLXNlcmllLWEtYWdnaW9ybmF0YS5odG1s")
ROSE_INDEX_URL = decode("aHR0cHM6Ly93d3cuZmFudGFjYWxjaW9wZWRpYS5jb20vcm9zZS1zZXJpZS1hLw==")

# Scraping
RUOLI = ["Portieri", "Difensori", "Centrocampisti", "Trequartisti", "Attaccanti"]
MAX_WORKERS = 5  # basso per non farsi bannare da FPD (con ~2s sleep/pagina: full scrape ~4min)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
FORCE_SCRAPE_URLS = True # Forza il re-scraping degli URL dei giocatori
