# config.py
import os
import base64


def decode(stringa):
    return base64.b64decode(stringa).decode("utf-8")


# Percorsi dei file
DATA_DIR = "data"
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
GIOCATORI_URLS_FILE = os.path.join(DATA_DIR, "giocatori_urls.txt")
GIOCATORI_CSV = os.path.join(DATA_DIR, "_giocatori.csv")
PLAYERS_CSV = os.path.join(DATA_DIR, "_players.csv")
CONVENIENZA_CSV = os.path.join(OUTPUT_DIR, "convenienza.csv")
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, "fantacalcio_analysis.xlsx")

# URLS
ANNO_CORRENTE = 2025
FSTATS_ANNO = 2024
BASEURL_FPEDIA = decode("aHR0cHM6Ly93d3cuZmFudGFjYWxjaW9wZWRpYS5jb20=")
BASEURL_FSTATS = decode("aHR0cHM6Ly9hcGkuYXBwLmZhbnRhZ29hdC5pdC9hcGk=")
FPEDIA_URL = f"{BASEURL_FPEDIA}/lista-calciatori-serie-a/"
FSTATS_LOGIN_URL = f"{BASEURL_FSTATS}/account/login/"
FSTATS_PLAYERS_URL = f"{BASEURL_FSTATS}/v1/zona/player/?page_size=1000&page=1&season={str(FSTATS_ANNO)}%2F{str(FSTATS_ANNO+1)[-2:]}&ordering="

# Scraping
RUOLI = ["Portieri", "Difensori", "Centrocampisti", "Trequartisti", "Attaccanti"]
MAX_WORKERS = 5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Costanti per il calcolo della convenienza
PESO_FANTAMEDIA = 0.6
PESO_PUNTEGGIO = 0.4
PREZZO_MINIMO = 1
PREZZO_MASSIMO = 500
CONVENIENZA_MINIMA = 0.5
