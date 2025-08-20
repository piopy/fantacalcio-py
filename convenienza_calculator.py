# convenienza_calculator.py
import pandas as pd
import ast
from loguru import logger
from config import ANNO_CORRENTE

# --- Funzioni per FPEDIA ---

skills_mapping = {
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


def calcola_convenienza_fpedia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola due indici di convenienza per i dati di FPEDIA:
    1. 'Convenienza': basata sulle performance stagionali (presenze, fantamedia).
    2. 'Convenienza Potenziale': basata sul valore intrinseco del giocatore (Punteggio, Skills),
       utile soprattutto a inizio campionato o con poche presenze.
    """
    if df.empty:
        logger.warning("DataFrame FPEDIA è vuoto. Calcolo saltato.")
        return df

    # --- Calcolo Convenienza (basata su presenze) ---
    res_convenienza = []
    df_calc = df.copy()

    numeric_cols = [
        f"Fantamedia anno {ANNO_CORRENTE-2}-{ANNO_CORRENTE-1}",
        "Partite giocate",
        f"Fantamedia anno {ANNO_CORRENTE-1}-{ANNO_CORRENTE}",
        "Presenze campionato corrente",
        "Punteggio",
        "Buon investimento",
        "Resistenza infortuni",
    ]
    for col in numeric_cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce").fillna(0)

    giocatemax = df_calc["Presenze campionato corrente"].max()
    if giocatemax == 0:
        giocatemax = 1

    for _, row in df_calc.iterrows():
        appetibilita = 0
        fantamedia_prec = row.get(
            f"Fantamedia anno {ANNO_CORRENTE-2}-{ANNO_CORRENTE-1}", 0
        )
        partite_prec = row.get("Partite giocate", 0)
        fantamedia_corr = row.get(
            f"Fantamedia anno {ANNO_CORRENTE-1}-{ANNO_CORRENTE}", 0
        )
        partite_corr = row.get("Presenze campionato corrente", 0)
        punteggio = row.get("Punteggio", 1)

        if partite_prec > 0:
            appetibilita += fantamedia_prec * (partite_prec / 38) * 0.20
        if partite_corr > 5:
            appetibilita += fantamedia_corr * (partite_corr / giocatemax) * 0.80
        elif partite_prec > 0:
            appetibilita = fantamedia_prec * (partite_prec / 38)

        appetibilita = appetibilita * punteggio * 0.30
        pt = punteggio if punteggio != 0 else 1
        appetibilita = (appetibilita / pt) * 100 / 40

        try:
            skills_list = ast.literal_eval(row.get("Skills", "[]"))
            plus = sum(skills_mapping.get(skill, 0) for skill in skills_list)
            appetibilita += plus
        except (ValueError, SyntaxError):
            pass

        if row.get("Nuovo acquisto", False):
            appetibilita -= 2
        if row.get("Buon investimento", 0) == 60:
            appetibilita += 3
        if row.get("Consigliato prossima giornata", False):
            appetibilita += 1
        if row.get("Trend", "") == "UP":
            appetibilita += 2
        if row.get("Infortunato", False):
            appetibilita -= 1
        if row.get("Resistenza infortuni", 0) > 60:
            appetibilita += 4
        elif row.get("Resistenza infortuni", 0) == 60:
            appetibilita += 2

        res_convenienza.append(appetibilita)

    df["Convenienza"] = res_convenienza
    logger.debug("Indice 'Convenienza' calcolato per FPEDIA.")

    # --- Calcolo Convenienza Potenziale (indipendente da presenze) ---
    res_potenziale = []
    for _, row in df_calc.iterrows():
        potenziale = row.get("Punteggio", 0)
        try:
            skills_list = ast.literal_eval(row.get("Skills", "[]"))
            plus = sum(skills_mapping.get(skill, 0) for skill in skills_list)
            potenziale += plus * 2  # Diamo più peso alle skill nel potenziale
        except (ValueError, SyntaxError):
            pass
        res_potenziale.append(potenziale)

    df["Convenienza Potenziale"] = res_potenziale
    logger.debug("Indice 'Convenienza Potenziale' calcolato per FPEDIA.")

    return df


# --- Funzioni per FSTATS ---


def calcola_convenienza_FSTATS(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola due indici di convenienza per i dati di FSTATS:
    1. 'Convenienza': basata sulle performance stagionali (presenze, fantamedia).
    2. 'Convenienza Potenziale': basata sul valore intrinseco (fantacalcioFantaindex) e potenziale
       statistico (xG, xA), utile soprattutto a inizio campionato.
    """
    if df.empty:
        logger.warning("DataFrame FSTATS è vuoto. Calcolo saltato.")
        return df

    df_calc = df.copy()
    numeric_cols = [
        "goals",
        "assists",
        "yellowCards",
        "redCards",
        "xgFromOpenPlays",
        "xA",
        "presences",
        "fanta_avg",
        "fantacalcioFantaindex",
    ]
    for col in numeric_cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors="coerce").fillna(0)

    # --- Calcolo Convenienza (basata su presenze) ---
    df_con_presenze = df_calc[df_calc["presences"] > 0].reset_index(drop=True)
    if not df_con_presenze.empty:
        bonus_score = (df_con_presenze["goals"] * 3) + (df_con_presenze["assists"] * 1)
        malus_score = (df_con_presenze["yellowCards"] * 0.5) + (
            df_con_presenze["redCards"] * 1
        )
        bonus_per_presence = bonus_score / df_con_presenze["presences"]
        malus_per_presence = malus_score / df_con_presenze["presences"]
        potential_score = (
            df_con_presenze["xgFromOpenPlays"] + df_con_presenze["xA"]
        ) / df_con_presenze["presences"]

        convenienza = (
            df_con_presenze["fanta_avg"] * 0.6
            + bonus_per_presence * 0.25
            + potential_score * 0.15
            - malus_per_presence * 0.2
        )
        df_con_presenze["Convenienza"] = (
            (convenienza / convenienza.max()) * 100 if not convenienza.empty else 0
        )
        df = df.merge(df_con_presenze[["Nome", "Convenienza"]], on="Nome", how="left")
        logger.debug("Indice 'Convenienza' calcolato per FSTATS.")
    else:
        df["Convenienza"] = 0
        logger.warning(
            "Nessun giocatore con presenze in FSTATS. 'Convenienza' impostata a 0."
        )

    # --- Calcolo Convenienza Potenziale (indipendente da presenze) ---
    potential_stats = (
        df_calc["xgFromOpenPlays"] + df_calc["xA"]
    ) * 2  # Pondera il potenziale xG/xA
    potenziale = df_calc["fantacalcioFantaindex"] + potential_stats

    df_calc["Convenienza Potenziale"] = (
        (potenziale / potenziale.max()) * 100 if not potenziale.empty else 0
    )
    df = df.merge(df_calc[["Nome", "Convenienza Potenziale"]], on="Nome", how="left")
    logger.debug("Indice 'Convenienza Potenziale' calcolato per FSTATS.")

    df.fillna({"Convenienza": 0, "Convenienza Potenziale": 0}, inplace=True)
    return df
