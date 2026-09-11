# data_processor.py
import pandas as pd
from loguru import logger
import config
import os


def load_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads the two CSV files into pandas DataFrames, handling missing or empty files.
    """
    df_fpedia = pd.DataFrame()
    df_FSTATS = pd.DataFrame()

    if (
        os.path.exists(config.GIOCATORI_CSV)
        and os.path.getsize(config.GIOCATORI_CSV) > 0
    ):
        try:
            df_fpedia = pd.read_csv(config.GIOCATORI_CSV)
            logger.debug("FPEDIA DataFrame loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading {config.GIOCATORI_CSV}: {e}")
    else:
        logger.warning(f"{config.GIOCATORI_CSV} not found or is empty.")

    if os.path.exists(config.PLAYERS_CSV) and os.path.getsize(config.PLAYERS_CSV) > 0:
        try:
            df_FSTATS = pd.read_csv(config.PLAYERS_CSV, sep=";")
            logger.debug("FSTATS DataFrame loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading {config.PLAYERS_CSV}: {e}")
    else:
        logger.warning(f"{config.PLAYERS_CSV} not found or is empty.")

    return df_fpedia, df_FSTATS


def process_fpedia_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes and cleans the DataFrame from FPEDIA.
    """
    if df.empty:
        logger.warning("FPEDIA DataFrame is empty. Skipping processing.")
        return df

    logger.debug("Processing FPEDIA data...")

    numeric_cols = [
        f"Fantamedia anno {config.ANNO_CORRENTE-2}-{config.ANNO_CORRENTE-1}",
        "Partite giocate",
        f"Fantamedia anno {config.ANNO_CORRENTE-1}-{config.ANNO_CORRENTE}",
        "Presenze campionato corrente",
        "Punteggio",
        "Nuovo acquisto",
        "Buon investimento",
        "Consigliato prossima giornata",
        "Resistenza infortuni",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            logger.warning(
                f"Column '{col}' not found in FPEDIA data. It will be created with value 0."
            )
            df[col] = 0

    if "Skills" not in df.columns:
        df["Skills"] = "[]"
    else:
        df["Skills"] = df["Skills"].fillna("[]")

    logger.info("FPEDIA data processed.")
    return df


def process_FSTATS_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes and cleans the DataFrame from FSTATS.
    It renames the original columns to a consistent format.
    """
    if df.empty:
        logger.warning("FSTATS DataFrame is empty. Skipping processing.")
        return df

    logger.debug("Processing FSTATS data...")

    # Rename columns for clarity and consistency
    rename_map = {
        "name": "Nome",
        "team": "Squadra",
        "fantacalcioPosition": "Ruolo",  # Using the specific fantacalcio role
        "appearances": "presences",
        "pagella": "avg",
        "fantacalcioRanking": "fanta_avg",
    }
    df = df.rename(columns=rename_map)

    # Define the list of columns that should be numeric, using the NEW names
    numeric_cols = [
        "goals",
        "assists",
        "yellowCards",
        "redCards",
        "xgFromOpenPlays",
        "xA",
        "presences",
        "avg",
        "fanta_avg",
        "fantacalcioFantaindex",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            # This warning should now only appear for genuinely missing columns
            logger.warning(
                f"Column '{col}' not found in FSTATS data. It will be created with value 0."
            )
            df[col] = 0

    logger.info("FSTATS data processed.")
    return df
