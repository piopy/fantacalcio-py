import ast
import os
from random import randint
import time
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm
import pandas as pd
from loguru import logger

ruoli = ["Portieri", "Difensori", "Centrocampisti", "Trequartisti", "Attaccanti"]

skills = {
    "Fuoriclasse": 1,
    "Titolare": 3,
    "Buona Media": 2,
    "Goleador": 4,
    "Assistman": 2,
    "Piazzati": 2,
    "Rigorista": 5,
    "Giovane talento": 2,
    "Panchinaro": -4,
    "Falloso": -2,
    "Outsider": 2,
}


def get_giocatori(ruolo: str) -> list:

    html = requests.get(
        "https://www.fantacalciopedia.com/lista-calciatori-serie-a/"
        + ruolo.lower()
        + "/"
    )
    soup = BeautifulSoup(html.content, "html.parser")
    calciatori = []
    giocatori = soup.find_all("article")
    for giocatore in giocatori:
        calciatore = giocatore.find("a").get("href")
        calciatori.append(calciatore)

    return calciatori


def get_attributi(url: str) -> dict:
    time.sleep(randint(0, 2000) / 1000)
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


def appetibilita(df: pd.DataFrame) -> float:
    # cleaning
    for col in df.columns:
        df.loc[df[col] == "nd", col] = 0

    # appetibilità =( Fantamedia anno scorso * Partite giocate anno scorso/38 * peso
    #              + Fantamedia anno corrente * Partite giocate anno corrente/giornata * 100-peso )/ quotazione
    #              + skills + altri parametri
    res = []
    giocatemax = 1

    for index, row in df.iterrows():
        if int(row[-1]) > giocatemax:
            giocatemax = row[-1]

    for index, row in df.iterrows():
        appetibilita = 0
        appetibilita_today = 0

        # media pesata fantamedia
        if int(row[5]) > 0:
            appetibilita += float(row[7]) * int(row[5]) / 38   *20/100 #era row 2
        
        if not (
            df.columns[2].split(" ")[-1] == df.columns[6].split(" ")[-1]
            and int(row[-1]) > 5
        ):  # stesso anno
            appetibilita = (
                appetibilita * float(row[6]) * int(row[-1]) / giocatemax *80/100
            )  
        else: 
            appetibilita = float(row[7]) * int(row[5]) / 38 

        # media pesata fantamedia * convenienza rispetto alla quotazione * media scorso anno
        appetibilita=appetibilita*row['Punteggio']*30/100
        if float(row[1]) == 0: pt=1
        else: pt=float(row[1])
        appetibilita = (
             appetibilita / pt * 100 / 40 
        ) 

        # skills
        try:
            valori = ast.literal_eval(row[-9])
            plus = 0
            for skill in valori:
                plus += skills[skill]
            appetibilita += plus
        except:
            pass

        if row["Nuovo acquisto"]:
            appetibilita -= 2
        if row["Buon investimento"] == 60:
            appetibilita += 3
        if row["Consigliato prossima giornata"]:
            appetibilita += 1
        if row["Trend"] == "UP":
            appetibilita += 2
        if row["Infortunato"]:
            appetibilita -= 1
        if row["Resistenza infortuni"] > 60:
            appetibilita += 4
        if row["Resistenza infortuni"] == 60:
            appetibilita += 2

        res.append(appetibilita)

    return res


if __name__ == "__main__":
    giocatori_urls = []
    if not os.path.exists("giocatori_urls.txt"):
        for i in tqdm(range(0, len(ruoli), 1)):
            lista = get_giocatori(ruoli[i])
            [giocatori_urls.append(el) for el in lista]
        with open(r"giocatori_urls.txt", "w") as fp:
            for item in giocatori_urls:
                fp.write("%s\n" % item)
            logger.debug("URL scritti")
    else:
        logger.debug("Leggo la lista giocatori")
        with open("giocatori_urls.txt", "r") as fp:
            giocatori_urls = fp.readlines()

    if not os.path.exists("giocatori.csv"):
        giocatori = []
        for i in tqdm(range(0, len(giocatori_urls), 1)):
            giocatore = get_attributi(giocatori_urls[i])
            giocatori.append(giocatore)
        df = pd.DataFrame.from_dict(giocatori)
        df.to_csv("giocatori.csv", index=False)
        
        logger.debug("CSV scritto")
    else:
        logger.debug("Leggo il dataset giocatori")
        df = pd.read_csv("giocatori.csv")

    df["Convenienza"] = appetibilita(df)

    # riordino le colonne come piace a me
    temp = df.columns
    df = df[
        [
            temp[11],
            temp[0],
            temp[18],
            temp[1],
            temp[21],
            temp[19],
            temp[12],
            temp[20],
            temp[6],
            temp[2],
            temp[5],
            temp[7],
            temp[3],
            temp[4],
            temp[16],
            temp[17],
            temp[8],
            temp[9],
            temp[10],
            temp[13],
            temp[14],
            temp[15],
        ]
    ]
    df.sort_values(by="Convenienza", ascending=False)

    # df.to_csv("giocatori_appet.csv", index=False)
    df.to_excel("giocatori_excel.xls")
    logger.debug("Finito!")