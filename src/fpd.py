# fpd.py — scraping FPD (nuovo main). Ex data_retriever.py senza FSTATS morto.
import os
import re
import time
from datetime import date
from random import randint
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from loguru import logger
from dotenv import load_dotenv
import pandas as pd
import concurrent.futures

from src import config

load_dotenv()


def get_giocatori_urls(force=True) -> list:
    """Scrapes FPD to get all player URLs."""
    giocatori_urls = []
    if not os.path.exists(config.GIOCATORI_URLS_FILE) or force:
        logger.debug("Scraping player URLs from FPD...")
        for ruolo in tqdm(config.RUOLI):
            url = config.FPD_URL + ruolo.lower() + "/"
            try:
                response = requests.get(url, headers=config.HEADERS)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                for giocatore in soup.find_all("article"):
                    calciatore_url = giocatore.find("a").get("href")
                    if calciatore_url:
                        giocatori_urls.append(calciatore_url)
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to retrieve URLs for role '{ruolo}': {e}")
                continue

        # Roles overlap on FPD (e.g. Trequartisti are also listed under Centrocampisti)
        giocatori_urls = list(dict.fromkeys(giocatori_urls))

        if not giocatori_urls:
            logger.warning(
                "No player URLs were scraped from FPD. "
                "The website structure may have changed, or the request was blocked."
            )
        else:
            with open(config.GIOCATORI_URLS_FILE, "w", encoding="utf-8") as fp:
                for item in giocatori_urls:
                    fp.write(f"{item}\n")
            logger.debug(f"{len(giocatori_urls)} player URLs saved.")
    else:
        logger.debug("Reading player URLs from cache.")
        with open(config.GIOCATORI_URLS_FILE, "r", encoding="utf-8") as fp:
            giocatori_urls = fp.readlines()
    return [url.strip() for url in giocatori_urls]


def get_attributi_giocatore(url: str) -> dict:
    """Scrapes a single player's page on FPD for their attributes."""
    logger.debug(f"Scraping attributes for player from URL: {url}")
    time.sleep(randint(1200, 3000) / 1000)  # throttle anti-ban: ~2s medi per request
    attributi = dict()
    html = requests.get(url.strip(), headers=config.HEADERS)
    soup = BeautifulSoup(html.content, "html.parser")

    attributi["Nome"] = soup.select_one("h1").get_text().strip()

    selettore = "div.col_one_fourth:nth-of-type(1) span.stickdan"
    attributi["Punteggio"] = soup.select_one(selettore).text.strip().replace("/100", "")

    selettore = "	div.col_one_fourth:nth-of-type(n+2) div"
    medie = [el.find("span").text.strip() for el in soup.select(selettore)]
    anni = [
        el.find("strong").text.split(" ")[-1].strip() for el in soup.select(selettore)
    ]
    i = 0
    for anno in anni:
        attributi[f"Fantamedia anno {anno}"] = medie[i]
        i += 1

    selettore = "div.col_one_third:nth-of-type(2) div"
    stats_ultimo_anno = soup.select_one(selettore)
    parametri = [
        el.text.strip().replace(":", "") for el in stats_ultimo_anno.find_all("strong")
    ]
    valori = [el.text.strip() for el in stats_ultimo_anno.find_all("span")]
    attributi.update(dict(zip(parametri, valori)))

    selettore = ".col_one_third.col_last div"
    stats_previste = soup.select_one(selettore)
    parametri = [
        el.text.strip().replace(":", "") for el in stats_previste.find_all("strong")
    ]
    valori = [el.text.strip() for el in stats_previste.find_all("span")]
    attributi.update(dict(zip(parametri, valori)))

    selettore = ".label12 span.label"
    ruolo = soup.select_one(selettore)
    attributi["Ruolo"] = ruolo.get_text().strip()

    selettore = "span.stickdanpic"
    skills = [el.text for el in soup.select(selettore)]
    attributi["Skills"] = skills

    selettore = "div.progress-percent"
    investimento = soup.select(selettore)[2]
    attributi["Buon investimento"] = investimento.text.replace("%", "")

    selettore = "div.progress-percent"
    investimento = soup.select(selettore)[3]
    attributi["Resistenza infortuni"] = investimento.text.replace("%", "")

    selettore = "img.inf_calc"
    try:
        consigliato = soup.select_one(selettore).get("title")
        if "Consigliato per la giornata" in consigliato:
            attributi["Consigliato prossima giornata"] = True
        else:
            attributi["Consigliato prossima giornata"] = False

    except:
        attributi["Consigliato prossima giornata"] = False

    selettore = "span.new_calc"
    nuovo = soup.select_one(selettore)
    if not nuovo == None:
        attributi["Nuovo acquisto"] = True
    else:
        attributi["Nuovo acquisto"] = False

    selettore = "img.inf_calc"
    try:
        infortunato = soup.select_one(selettore).get("title")
        if "Infortunato" in infortunato:
            attributi["Infortunato"] = True
        else:
            attributi["Infortunato"] = False

    except:
        attributi["Infortunato"] = False

    selettore = "#content > div > div.section.nobg.nomargin > div > div > div:nth-child(2) > div.col_three_fifth > div.promo.promo-border.promo-light.row > div:nth-child(3) > div:nth-child(1) > div > img"
    squadra = soup.select_one(selettore).get("title").split(":")[1].strip()
    attributi["Squadra"] = squadra

    selettore = "	div.col_one_fourth:nth-of-type(n+2) div"
    try:
        trend = soup.select(selettore)[0].find("i").get("class")[1]
        if trend == "icon-arrow-up":
            attributi["Trend"] = "UP"
        else:
            attributi["Trend"] = "DOWN"
    except:
        attributi["Trend"] = "STABLE"

    selettore = "div.col_one_fourth:nth-of-type(2) span.rouge"
    presenze_attuali = soup.select_one(selettore).text
    attributi["Presenze campionato corrente"] = presenze_attuali

    txt_all = soup.get_text("\n", strip=True)

    # anagrafica: età + nazionalità (utile es. Coppa d'Africa)
    attributi["Eta"] = ""
    attributi["Nazionalita"] = ""
    m = re.search(r"Data nascita:\s*(\d{2})-(\d{2})-(\d{4})", txt_all)
    if m:
        try:
            born = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            today = date.today()
            attributi["Eta"] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except ValueError:
            pass
    m = re.search(r"Nazionalit.:\s*([A-Za-z ]+)", txt_all)
    if m:
        attributi["Nazionalita"] = m.group(1).strip()

    # consiglio editoriale più recente + stagione di riferimento
    attributi["Consiglio_anno"] = ""
    attributi["Consiglio_testo"] = ""
    cons = soup.select(".mc_hookEvolution p")
    if cons:
        label = cons[0].find("strong")
        label_txt = label.get_text(strip=True) if label else ""
        attributi["Consiglio_anno"] = label_txt
        attributi["Consiglio_testo"] = cons[0].get_text(" ", strip=True)[:800]
        if not re.search(r"(19|20)\d{2}", label_txt):
            y = re.search(r"(19|20)\d{2}", attributi["Consiglio_testo"])
            if y:
                attributi["Consiglio_anno"] = f"{label_txt} {y.group(0)}".strip()

    # forma ultime gare (chart FantaVoto embedded)
    attributi["Forma_serie"] = ""
    attributi["Forma_media"] = ""
    html = str(soup)
    i = html.find("chartjs-0")
    if i > 0:
        win = html[i:i + 1500]
        md = re.search(r"datasets.*?data.*?\[(.*?)\]", win, re.S)
        if md:
            try:
                voti = [float(x) for x in md.group(1).split(",") if x.strip()]
                if voti:
                    attributi["Forma_serie"] = "|".join(str(v) for v in voti)
                    attributi["Forma_media"] = round(sum(voti) / len(voti), 2)
            except ValueError:
                pass

    # simili in reparto (nomi; punteggio nostro a carico frontend/merge)
    attributi["Simili"] = ""
    sim = [t for t in soup.find_all("h2") if "simili" in t.get_text().lower()]
    if sim:
        box = sim[0].find_parent("div")
        while box and len(box.find_all("a")) < 2:
            box = box.parent
        nomi = []
        for a in box.find_all("a", href=re.compile(r"/lista-calciatori-serie-a/\w+/\d+/")):
            t = a.get_text(" ", strip=True)
            if t:
                nomi.append(t[:60])
        attributi["Simili"] = "|".join(dict.fromkeys(nomi))

    return attributi


def scrape_fpd(force: bool = False):
    """
    Orchestrates the scraping of FPD.
    Fetches all player URLs and then scrapes each player's page for their attributes in parallel.
    Saves the data to a CSV file.
    """
    if os.path.exists(config.GIOCATORI_CSV):
        if force:
            logger.debug(f"Force flag is set. Re-scraping {config.GIOCATORI_CSV}.")
            os.remove(config.GIOCATORI_CSV)
        else:
            logger.debug(f"{config.GIOCATORI_CSV} already exists. Skipping scraping.")
            return

    urls = get_giocatori_urls(config.FORCE_SCRAPE_URLS)
    giocatori = []
    logger.debug("Scraping individual player data from website...")

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=config.MAX_WORKERS
    ) as executor:
        future_to_url = {
            executor.submit(get_attributi_giocatore, url): url for url in urls
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_url), total=len(urls)
        ):
            url = future_to_url[future]
            try:
                attributi = future.result()
                if attributi:
                    giocatori.append(attributi)
            except Exception as exc:
                logger.error(f"{url} generated an exception: {exc}")

    df = pd.DataFrame(giocatori)
    df.to_csv(config.GIOCATORI_CSV, index=False)
    logger.debug("FPD data saved to CSV.")
