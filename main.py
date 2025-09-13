# main.py
import os
from loguru import logger
import pandas as pd
import json

import data_retriever
import data_processor
import convenienza_calculator
import fuzzy_matcher
import config


def merge_datasets_with_mapping(
    df_fpedia_final, df_fstats_final, mapping_file=fuzzy_matcher.OUTPUT_FILE
):
    """
    Unisce i due dataset usando il mapping dei nomi generato dal fuzzymatcher
    """
    logger.info("Starting dataset merge with fuzzy mapping...")

    # carica il mapping
    if not os.path.exists(mapping_file):
        logger.warning(f"Mapping file {mapping_file} not found. Skipping merge.")
        return pd.DataFrame()

    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    mapping = mapping_data.get("mapping", {})
    probably_mapped_ns = mapping_data.get("probably_mapped_ns", {})

    # unisci i dizionari di mapping
    all_mapping = {**mapping, **probably_mapped_ns}

    logger.info(f"Found {len(all_mapping)} player mappings")

    # MERGING
    df_fpedia_merge = df_fpedia_final.copy()
    df_fstats_merge = df_fstats_final.copy()

    fpedia_cols = {
        col: f"fpedia_{col}"
        for col in df_fpedia_merge.columns
        if col not in ["Nome", "Ruolo", "Squadra"]
    }
    fstats_cols = {
        col: f"fstats_{col}"
        for col in df_fstats_merge.columns
        if col not in ["Nome", "Ruolo", "Squadra"]
    }

    df_fpedia_merge = df_fpedia_merge.rename(columns=fpedia_cols)
    df_fstats_merge = df_fstats_merge.rename(columns=fstats_cols)

    df_fpedia_merge["mapped_name"] = df_fpedia_merge["Nome"].map(all_mapping)
    df_fstats_merge["mapped_name"] = (
        df_fstats_merge["fstats_firstname"].fillna("")
        + " "
        + df_fstats_merge["fstats_lastname"].fillna("")
    ).str.strip()


    df_merged = pd.merge(
        df_fpedia_merge,
        df_fstats_merge,
        on="mapped_name",
        how="inner",
        suffixes=("_fpedia", "_fstats"),
    )

    priority_cols = [
        "Nome_fpedia",  # Nome originale FPEDIA
        "mapped_name",  # Nome mappato FSTATS
        "Ruolo",
        "Squadra",
        "fpedia_Convenienza Potenziale",
        "fstats_Convenienza Potenziale",
        "fpedia_Convenienza",
        "fstats_Convenienza",
        "fpedia_Punteggio",
        "fstats_fantacalcioFantaindex",
        "fstats_fanta_avg",
        "fstats_presences",
    ]
    remaining_cols = [col for col in df_merged.columns if col not in priority_cols]
    final_col_order = [
        col for col in priority_cols if col in df_merged.columns
    ] + remaining_cols

    df_merged = df_merged[final_col_order]

    logger.info(f"Merged dataset contains {df_merged.shape[0]} players")
    return df_merged


def main():
    """
    Main script to run the entire Fantacalcio analysis pipeline.
    It now runs two separate pipelines for FPEDIA and FSTATS,
    generates both performance-based and potential-based convenience indexes,
    and creates a unified analysis using fuzzy matching.
    """
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    logger.info("Starting Fantacalcio analysis pipeline...")
    logger.info("Step 1: Retrieving data from all sources...")
    data_retriever.scrape_fpedia(force=config.FORCE_SCRAPING_MAIN)
    data_retriever.fetch_FSTATS_data(force=config.FORCE_SCRAPING_MAIN)
    logger.info("Data retrieval complete.")

    # 2. Generate fuzzy mapping
    logger.info("Step 2: Generating fuzzy name mapping...")
    try:
        fuzzy_matcher.start_matching(
            df_giocatori_path=config.GIOCATORI_CSV,
            df_players_path=config.PLAYERS_CSV,
        )
        logger.info("Fuzzy mapping complete.")
    except Exception as e:
        logger.error(f"Error in fuzzy matching: {e}")

    # 3. Load dataframes
    df_fpedia, df_FSTATS = data_processor.load_dataframes()

    df_fpedia_final = None
    df_fstats_final = None

    # --- Pipeline for FPEDIA ---
    if not df_fpedia.empty:
        logger.info("--- Starting FPEDIA Pipeline ---")

        df_processed = data_processor.process_fpedia_data(df_fpedia)
        df_final = convenienza_calculator.calcola_convenienza_fpedia(df_processed)

        df_final = df_final.sort_values(by="Convenienza Potenziale", ascending=False)

        # Define a comprehensive and ordered list of columns for the final output
        output_columns = [
            # Key Info
            "Nome",
            "Ruolo",
            "Squadra",
            # Calculated Indexes
            "Convenienza Potenziale",
            "Convenienza",
            "Punteggio",
            # Current Season Stats
            f"Fantamedia anno {config.ANNO_CORRENTE-1}-{config.ANNO_CORRENTE}",
            f"Presenze campionato corrente",
            # Previous Season Stats
            f"Fantamedia anno {config.ANNO_CORRENTE-2}-{config.ANNO_CORRENTE-1}",
            "Partite giocate",
            # Qualitative Info
            "Trend",
            "Skills",
            "Consigliato prossima giornata",
            "Buon investimento",
            "Resistenza infortuni",
            "Infortunato",
            # Legacy
            f"FM su tot gare {config.ANNO_CORRENTE-1}-{config.ANNO_CORRENTE}",
            "Presenze previste",
            "Gol previsti",
            "Assist previsti",
            "Nuovo acquisto",
        ]
        final_columns = [col for col in output_columns if col in df_final.columns]

        output_path = os.path.join(config.OUTPUT_DIR, "fpedia_analysis.xlsx")
        df_final[final_columns].to_excel(output_path, index=False)

        df_fpedia_final = df_final.copy()  # Salva per il merge

        logger.info(f"FPEDIA analysis complete. Results saved to {output_path}")
    else:
        logger.warning("FPEDIA DataFrame is empty. Pipeline skipped.")

    # --- Pipeline for FSTATS ---
    if not df_FSTATS.empty:
        logger.info("--- Starting FSTATS Pipeline ---")

        df_processed = data_processor.process_FSTATS_data(df_FSTATS)
        df_final = convenienza_calculator.calcola_convenienza_FSTATS(df_processed)

        df_final = df_final.sort_values(by="Convenienza Potenziale", ascending=False)

        # Define a comprehensive and ordered list of columns for the final output
        output_columns = [
            # Key Info
            "Nome",
            "Ruolo",
            "Squadra",
            # Calculated Indexes
            "Convenienza Potenziale",
            "Convenienza",
            "fantacalcioFantaindex",
            # Key Performance Indicators
            "fanta_avg",
            "avg",
            "presences",
            # Core Stats
            "goals",
            "assists",
            # Potential Stats
            "xgFromOpenPlays",
            "xA",
            # Disciplinary
            "yellowCards",
            "redCards",
            # Legacy
            "injured",
            "banned",
            "mantra_position",
            "fantacalcio_position",
            "birth_date",
            "foot_name",
            "fantacalcioPlayerId",
            "fantacalcioTeamName",
            "appearances",
            "matchesInStart",
            "mins_played",
            "pagella",
            "fantacalcioRanking",
            "fantacalcioFantaindex",
            "fantacalcioPosition",
            "goals90min",
            "goalsFromOpenPlays",
            "xgFromOpenPlays/90min",
            "xA90min",
            "successfulPenalties",
            "penalties",
            "gkPenaltiesSaved",
            "gkCleanSheets",
            "gkConcededGoals",
            "openPlaysGoalsConceded",
            "openPlaysXgConceded",
            "fantamediaPred",
            "fantamediaPredRoundId",
            "matchConvocation",
            "matchesWithGrade",
            "perc_matchesStarted",
            "perc_matchesWithGrade",
            "percMinsPlayed",
            "expectedFantamediaMean",
            "External_breakout_Index",
            "Shot_on_goal_Index",
            "Offensive_actions_Index",
            "Pass_forward_accuracy_Index",
            "Air_challenge_offensive_Index",
            "Cross_accuracy_Index",
            "Converge_in_the_center_Index",
            "Accompany_the_offensive_action_Index",
            "Offensive_verticalization_Index",
            "Received_pass_Index",
            "Attacking_area_Index",
            "Offensive_field_presence_Index",
            "Pass_accuracy_Index",
            "Pass_leading_chances_Index",
            "Deep_runs_Index",
            "Defense_solidity_Index",
            "Set_piece_attack_Index",
            "Shot_on_target_Index",
            "Dribbles_successful_Index",
            "firstname",
            "lastname",
        ]
        final_columns = [col for col in output_columns if col in df_final.columns]

        output_path = os.path.join(config.OUTPUT_DIR, "FSTATS_analysis.xlsx")
        df_final[final_columns].to_excel(output_path, index=False)

        df_fstats_final = df_final.copy()  # Salva per il merge

        logger.info(f"FSTATS analysis complete. Results saved to {output_path}")
    else:
        logger.warning("FSTATS DataFrame is empty. Pipeline skipped.")

    # 4. Create unified analysis if both datasets are available
    if df_fpedia_final is not None and df_fstats_final is not None:
        logger.info("--- Creating Unified Analysis ---")
        df_unified = merge_datasets_with_mapping(df_fpedia_final, df_fstats_final)

        if not df_unified.empty:
            unified_output_path = os.path.join(
                config.OUTPUT_DIR, "unified_analysis.xlsx"
            )
            df_unified.to_excel(unified_output_path, index=False)
            logger.info(
                f"Unified analysis complete. Results saved to {unified_output_path}"
            )
        else:
            logger.warning("Unified analysis resulted in empty DataFrame.")

    logger.info("Fantacalcio analysis pipeline finished.")


if __name__ == "__main__":
    main()
