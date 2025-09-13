#!/usr/bin/env python3
"""
Fantacalcio-PY CLI - Modern command line interface for fantacalcio analysis
"""
import os
import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

# Import existing modules
import data_retriever
import data_processor
import convenienza_calculator
import fuzzy_matcher
import config
import json


console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--config-file", "-c", type=click.Path(exists=True), help="Custom config file"
)
@click.pass_context
def cli(ctx, verbose, config_file):
    """
    🏆 Fantacalcio-PY - Advanced fantasy football analysis tool

    Analyze player data from multiple sources to find the best value picks
    for your fantasy football auction.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_file"] = config_file

    # Configure logging
    logger.remove()  # Remove default handler
    if verbose:
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        )
    else:
        logger.add(
            sys.stderr, level="INFO", format="<level>{level: <8}</level> | {message}"
        )


@cli.command()
@click.option(
    "--source",
    "-s",
    type=click.Choice(["fpedia", "fstats", "all"]),
    default="all",
    help="Data source to scrape",
)
@click.option(
    "--force", "-f", is_flag=True, help="Force re-download even if cache exists"
)
@click.pass_context
def scrape(ctx, source, force):
    """
    📥 Download player data from external sources

    Scrapes data from FPEDIA and/or FSTATS depending on the source option.
    Uses intelligent caching to avoid unnecessary requests.
    """
    verbose = ctx.obj.get("verbose", False)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Setup directories
        task = progress.add_task("Setting up directories...", total=None)
        os.makedirs(config.DATA_DIR, exist_ok=True)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        progress.update(task, completed=True)

        if source in ["fpedia", "all"]:
            task = progress.add_task("Scraping FPEDIA data...", total=None)
            try:
                if force or not os.path.exists(config.GIOCATORI_CSV):
                    data_retriever.scrape_fpedia(force)
                    rprint("✅ [green]FPEDIA data scraped successfully[/green]")
                else:
                    rprint(
                        "ℹ️ [yellow]FPEDIA data already exists (use --force to re-download)[/yellow]"
                    )
                progress.update(task, completed=True)
            except Exception as e:
                rprint(f"❌ [red]Error scraping FPEDIA: {e}[/red]")

        if source in ["fstats", "all"]:
            task = progress.add_task("Fetching FSTATS data...", total=None)
            try:
                if force or not os.path.exists(config.PLAYERS_CSV):
                    data_retriever.fetch_FSTATS_data(force)
                    rprint("✅ [green]FSTATS data fetched successfully[/green]")
                else:
                    rprint(
                        "ℹ️ [yellow]FSTATS data already exists (use --force to re-download)[/yellow]"
                    )
                progress.update(task, completed=True)
            except Exception as e:
                rprint(f"❌ [red]Error fetching FSTATS: {e}[/red]")


@cli.command()
@click.option(
    "--source",
    "-s",
    type=click.Choice(["fpedia", "fstats", "all"]),
    default="all",
    help="Data source to analyze",
)
@click.option("--output", "-o", type=click.Path(), help="Custom output directory")
@click.option("--top", "-t", type=int, default=50, help="Show top N players in summary")
@click.pass_context
def analyze(ctx, source, output, top):
    """
    🔍 Process and analyze player data

    Calculates convenience indexes and generates Excel reports with
    detailed player analysis and recommendations.
    """
    verbose = ctx.obj.get("verbose", False)

    if output:
        config.OUTPUT_DIR = output
        os.makedirs(output, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Load data
        task = progress.add_task("Loading data files...", total=None)
        df_fpedia, df_fstats = data_processor.load_dataframes()
        progress.update(task, completed=True)

        # Store final dataframes for unified analysis
        df_fpedia_final = None
        df_fstats_final = None

        # Process FPEDIA
        if source in ["fpedia", "all"] and not df_fpedia.empty:
            task = progress.add_task("Processing FPEDIA data...", total=None)
            df_processed = data_processor.process_fpedia_data(df_fpedia)
            df_final = convenienza_calculator.calcola_convenienza_fpedia(df_processed)

            # Save results
            output_path = os.path.join(config.OUTPUT_DIR, "fpedia_analysis.xlsx")
            df_final_sorted = df_final.sort_values(
                by="Convenienza Potenziale", ascending=False
            )

            # Define comprehensive columns for output (EXACT copy from main.py)
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
            final_columns = [
                col for col in output_columns if col in df_final_sorted.columns
            ]

            # Save both Excel and JSON
            excel_path, json_path = _save_analysis_results(
                df_final_sorted[final_columns], "fpedia_analysis", "fpedia"
            )

            progress.update(task, completed=True)
            rprint(f"✅ [green]FPEDIA analysis saved to {excel_path}[/green]")
            rprint(f"📄 [blue]JSON export saved to {json_path}[/blue]")

            # Store for unified analysis
            df_fpedia_final = df_final.copy()

            # Show top players
            _show_top_players(df_final_sorted, "FPEDIA", top)

        # Process FSTATS
        if source in ["fstats", "all"] and not df_fstats.empty:
            task = progress.add_task("Processing FSTATS data...", total=None)
            df_processed = data_processor.process_FSTATS_data(df_fstats)
            df_final = convenienza_calculator.calcola_convenienza_FSTATS(df_processed)

            # Save results
            output_path = os.path.join(config.OUTPUT_DIR, "FSTATS_analysis.xlsx")
            df_final_sorted = df_final.sort_values(
                by="Convenienza Potenziale", ascending=False
            )

            # Define comprehensive columns for output (EXACT copy from main.py)
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
            ]
            final_columns = [
                col for col in output_columns if col in df_final_sorted.columns
            ]

            # Save both Excel and JSON
            excel_path, json_path = _save_analysis_results(
                df_final_sorted[final_columns], "FSTATS_analysis", "fstats"
            )

            progress.update(task, completed=True)
            rprint(f"✅ [green]FSTATS analysis saved to {excel_path}[/green]")
            rprint(f"📄 [blue]JSON export saved to {json_path}[/blue]")

            # Store for unified analysis
            df_fstats_final = df_final.copy()

            # Show top players
            _show_top_players(df_final_sorted, "FSTATS", top)

        # Create unified analysis if both datasets were processed
        if (source == "all" and
            df_fpedia_final is not None and df_fstats_final is not None):
            task = progress.add_task("Creating unified analysis...", total=None)

            # Create unified dataset using already processed data
            df_unified = _merge_datasets_with_mapping(df_fpedia_final, df_fstats_final)

            if not df_unified.empty:
                # Save unified results
                excel_path, json_path = _save_analysis_results(
                    df_unified, "unified_analysis", "unified"
                )

                progress.update(task, completed=True)
                rprint(f"✅ [green]Unified analysis saved to {excel_path}[/green]")
                rprint(f"📄 [blue]JSON export saved to {json_path}[/blue]")

                # Show top unified players
                _show_top_players(df_unified, "UNIFIED", top)
            else:
                progress.update(task, completed=True)
                rprint("⚠️ [yellow]Unified analysis resulted in empty dataset[/yellow]")


@cli.command()
@click.option(
    "--source",
    "-s",
    type=click.Choice(["fpedia", "fstats", "all"]),
    default="all",
    help="Data source for full pipeline",
)
@click.option("--force-scrape", is_flag=True, help="Force re-download of data")
@click.option("--top", "-t", type=int, default=20, help="Show top N players in summary")
@click.pass_context
def run(ctx, source, force_scrape, top):
    """
    🚀 Run the complete analysis pipeline

    Executes scraping, processing, and analysis in one command.
    This is equivalent to running 'scrape' followed by 'analyze'.
    """
    rprint("🏆 [bold blue]Starting Fantacalcio-PY Analysis Pipeline[/bold blue]")

    # Run scraping
    ctx.invoke(scrape, source=source, force=force_scrape)

    # Run analysis
    ctx.invoke(analyze, source=source, top=top)

    rprint("🎉 [bold green]Pipeline completed successfully![/bold green]")


@cli.command()
@click.option(
    "--source",
    "-s",
    type=click.Choice(["fpedia", "fstats"]),
    required=True,
    help="Data source to inspect",
)
@click.option("--role", "-r", help="Filter by player role (e.g., Portieri, Difensori)")
@click.option("--team", help="Filter by team name")
@click.option("--limit", "-l", type=int, default=10, help="Number of players to show")
def inspect(source, role, team, limit):
    """
    🔍 Inspect loaded data without full analysis

    Quick preview of the data to verify scraping worked correctly
    and explore player information before running analysis.
    """
    df_fpedia, df_fstats = data_processor.load_dataframes()

    if source == "fpedia":
        df = df_fpedia
        if df.empty:
            rprint(
                "❌ [red]No FPEDIA data found. Run 'fantacalcio scrape' first.[/red]"
            )
            return
    else:
        df = df_fstats
        if df.empty:
            rprint(
                "❌ [red]No FSTATS data found. Run 'fantacalcio scrape' first.[/red]"
            )
            return

    # Apply filters
    if role and "Ruolo" in df.columns:
        df = df[df["Ruolo"].str.contains(role, case=False, na=False)]

    if team and "Squadra" in df.columns:
        df = df[df["Squadra"].str.contains(team, case=False, na=False)]

    # Show results
    total_players = len(df)
    df_display = df.head(limit)

    rprint(f"\n📊 [bold]{source.upper()} Data Preview[/bold]")
    rprint(f"Total players: {total_players}")
    if role:
        rprint(f"Filtered by role: {role}")
    if team:
        rprint(f"Filtered by team: {team}")

    # Create a nice table
    table = Table(show_header=True, header_style="bold magenta")

    # Add key columns
    key_cols = ["Nome", "Ruolo", "Squadra"]
    if source == "fpedia":
        key_cols.extend(["Punteggio", "Presenze campionato corrente"])
    else:
        key_cols.extend(["fanta_avg", "presences"])

    for col in key_cols:
        if col in df_display.columns:
            table.add_column(col)

    for _, row in df_display.iterrows():
        values = []
        for col in key_cols:
            if col in row:
                val = str(row[col]) if pd.notna(row[col]) else "-"
                values.append(val)
        if values:
            table.add_row(*values)

    console.print(table)


@cli.command()
def status():
    """
    📋 Show current data status and configuration

    Displays information about available data files, configuration,
    and system status to help with troubleshooting.
    """
    table = Table(
        title="Fantacalcio-PY Status", show_header=True, header_style="bold cyan"
    )
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Check data files
    fpedia_exists = os.path.exists(config.GIOCATORI_CSV)
    fpedia_size = os.path.getsize(config.GIOCATORI_CSV) if fpedia_exists else 0
    fstats_exists = os.path.exists(config.PLAYERS_CSV)
    fstats_size = os.path.getsize(config.PLAYERS_CSV) if fstats_exists else 0

    table.add_row(
        "FPEDIA Data",
        "✅ Ready" if fpedia_exists and fpedia_size > 0 else "❌ Missing",
        f"{fpedia_size // 1024} KB" if fpedia_exists else "Not found",
    )

    table.add_row(
        "FSTATS Data",
        "✅ Ready" if fstats_exists and fstats_size > 0 else "❌ Missing",
        f"{fstats_size // 1024} KB" if fstats_exists else "Not found",
    )

    # Check output directory
    output_exists = os.path.exists(config.OUTPUT_DIR)
    table.add_row(
        "Output Directory",
        "✅ Ready" if output_exists else "❌ Missing",
        config.OUTPUT_DIR,
    )

    # Check .env file
    env_exists = os.path.exists(".env")
    table.add_row(
        "Environment Config",
        "✅ Found" if env_exists else "⚠️ Missing",
        ".env file for FSTATS credentials",
    )

    # Configuration
    table.add_row("Current Season", "ℹ️", str(config.ANNO_CORRENTE))
    table.add_row("FSTATS Season", "ℹ️", str(config.FSTATS_ANNO))

    console.print(table)

    if not env_exists:
        rprint("\n⚠️ [yellow]Warning: .env file not found![/yellow]")
        rprint(
            "Create a .env file with your FSTATS credentials to enable FSTATS data fetching."
        )



def _save_analysis_results(df, base_name, source_name):
    """Helper function to save analysis results in both Excel and JSON formats"""
    import pandas as pd

    # Excel output
    excel_path = os.path.join(config.OUTPUT_DIR, f"{base_name}.xlsx")
    df.to_excel(excel_path, index=False)

    # JSON output
    json_path = os.path.join(config.OUTPUT_DIR, f"{base_name}.json")
    data = {
        "metadata": {
            "source": source_name,
            "total_players": len(df),
            "generated_at": pd.Timestamp.now().isoformat(),
            "columns": list(df.columns)
        },
        "players": df.fillna("").to_dict("records")
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return excel_path, json_path


def _merge_datasets_with_mapping(df_fpedia_final, df_fstats_final, mapping_file=fuzzy_matcher.OUTPUT_FILE):
    """Merge datasets using fuzzy mapping"""
    import pandas as pd

    # Load mapping
    if not os.path.exists(mapping_file):
        rprint(f"⚠️ [yellow]Mapping file {mapping_file} not found. Skipping unified analysis.[/yellow]")
        return pd.DataFrame()

    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    mapping = mapping_data.get("mapping", {})
    probably_mapped_ns = mapping_data.get("probably_mapped_ns", {})
    all_mapping = {**mapping, **probably_mapped_ns}

    if not all_mapping:
        rprint("⚠️ [yellow]No player mappings found. Skipping unified analysis.[/yellow]")
        return pd.DataFrame()

    # Prepare datasets for merging
    df_fpedia_merge = df_fpedia_final.copy()
    df_fstats_merge = df_fstats_final.copy()

    # Rename columns to avoid conflicts
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

    # Create mapping keys
    df_fpedia_merge["mapped_name"] = df_fpedia_merge["Nome"].map(all_mapping)
    df_fstats_merge["mapped_name"] = (
        df_fstats_merge["fstats_firstname"].fillna("")
        + " "
        + df_fstats_merge["fstats_lastname"].fillna("")
    ).str.strip()

    # Merge
    df_merged = pd.merge(
        df_fpedia_merge,
        df_fstats_merge,
        on="mapped_name",
        how="inner",
        suffixes=("_fpedia", "_fstats"),
    )

    # Reorder columns
    priority_cols = [
        "Nome_fpedia",
        "mapped_name",
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

    return df_merged[final_col_order]


def _show_top_players(df, source_name, top_n):
    """Helper function to display top players in a nice table"""
    if df.empty:
        return

    rprint(f"\n🏆 [bold]Top {top_n} Players - {source_name}[/bold]")

    table = Table(show_header=True, header_style="bold green")
    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Role")
    table.add_column("Team")
    table.add_column("Convenience", justify="right", style="green")

    df_top = df.head(top_n)
    for idx, (_, row) in enumerate(df_top.iterrows(), 1):
        convenience = row.get("Convenienza Potenziale", row.get("Convenienza", 0))
        table.add_row(
            str(idx),
            str(row.get("Nome", "N/A")),
            str(row.get("Ruolo", "N/A")),
            str(row.get("Squadra", "N/A")),
            f"{convenience:.2f}" if pd.notna(convenience) else "N/A",
        )

    console.print(table)


if __name__ == "__main__":
    # Import pandas here to avoid circular import issues
    import pandas as pd

    cli()
