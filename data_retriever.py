# data_retriever.py
import os
import time
from random import randint
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from loguru import logger
from dotenv import load_dotenv
import pandas as pd
import concurrent.futures

import config

load_dotenv()


def get_giocatori_urls() -> list:
    """Scrapes FPEDIA to get all player URLs."""
    giocatori_urls = []
    if not os.path.exists(config.GIOCATORI_URLS_FILE):
        logger.debug("Scraping player URLs from FPEDIA...")
        for ruolo in tqdm(config.RUOLI):
            url = config.FPEDIA_URL + ruolo.lower() + "/"
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

        if not giocatori_urls:
            logger.warning(
                "No player URLs were scraped from FPEDIA. "
                "The website structure may have changed, or the request was blocked."
            )
        else:
            with open(config.GIOCATORI_URLS_FILE, "w") as fp:
                for item in giocatori_urls:
                    fp.write(f"{item}\n")
            logger.debug(f"{len(giocatori_urls)} player URLs saved.")
    else:
        logger.debug("Reading player URLs from cache.")
        with open(config.GIOCATORI_URLS_FILE, "r") as fp:
            giocatori_urls = fp.readlines()
    return [url.strip() for url in giocatori_urls]


def get_attributi_giocatore(url: str) -> dict:
    """Scrapes a single player's page on FPEDIA for their attributes."""
    logger.debug(f"Scraping attributes for player from URL: {url}")
    time.sleep(randint(1000, 8000) / 1000)
    attributi = dict()
    html = requests.get(url.strip())
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

    return attributi


def scrape_fpedia():
    """
    Orchestrates the scraping of FPEDIA.
    Fetches all player URLs and then scrapes each player's page for their attributes in parallel.
    Saves the data to a CSV file.
    """
    if os.path.exists(config.GIOCATORI_CSV):
        logger.debug(f"{config.GIOCATORI_CSV} already exists. Skipping scraping.")
        return

    urls = get_giocatori_urls()
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
    logger.debug("FPEDIA data saved to CSV.")


def fetch_FSTATS_data():
    """
    Logs into FSTATS, fetches player data from the API,
    and saves it to a CSV file.
    """
    if os.path.exists(config.PLAYERS_CSV):
        logger.debug(f"{config.PLAYERS_CSV} already exists. Skipping download.")
        return

    user = os.getenv("FSTATS_MAIL")
    password = os.getenv("FSTATS_PASSWORD")

    if not user or not password:
        logger.error("FSTATS credentials not found in .env file. Skipping download.")
        return

    # 1. Login and get token
    logger.debug("Logging into FSTATS...")
    login_payload = {"username": user, "password": password}
    headers = {"content-type": "application/json"}
    try:
        response = requests.post(
            config.FSTATS_LOGIN_URL, json=login_payload, headers=headers
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        logger.debug("Login successful.")
    except requests.exceptions.RequestException as e:
        logger.error(f"FSTATS login failed: {e}")
        return

    # 2. Fetch player data
    logger.debug("Fetching player data from FSTATS API...")
    auth_headers = {"authorization": f"Bearer {token}"}
    try:
        response = requests.get(config.FSTATS_PLAYERS_URL, headers=auth_headers)
        response.raise_for_status()
        players_data = response.json()["results"]

        df = pd.DataFrame(players_data)
        df.to_csv(config.PLAYERS_CSV, index=False, sep=";")
        logger.debug("FSTATS data saved to CSV.")
    except requests.exceptions.RequestException as e:
        logger.error(f"FSTATS data fetch failed: {e}")
