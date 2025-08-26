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
    MofNCompleteColumn
)
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

# Import existing modules
import data_retriever
import data_processor
import convenienza_calculator
import config


console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-file', '-c', type=click.Path(exists=True), help='Custom config file')
@click.pass_context
def cli(ctx, verbose, config_file):
    """
    🏆 Fantacalcio-PY - Advanced fantasy football analysis tool
    
    Analyze player data from multiple sources to find the best value picks
    for your fantasy football auction.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file
    
    # Configure logging
    logger.remove()  # Remove default handler
    if verbose:
        logger.add(sys.stderr, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    else:
        logger.add(sys.stderr, level="INFO", format="<level>{level: <8}</level> | {message}")


@cli.command()
@click.option('--source', '-s', 
              type=click.Choice(['fpedia', 'fstats', 'all']), 
              default='all',
              help='Data source to scrape')
@click.option('--force', '-f', is_flag=True, help='Force re-download even if cache exists')
@click.pass_context
def scrape(ctx, source, force):
    """
    📥 Download player data from external sources
    
    Scrapes data from FPEDIA and/or FSTATS depending on the source option.
    Uses intelligent caching to avoid unnecessary requests.
    """
    verbose = ctx.obj.get('verbose', False)
    
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
        
        if source in ['fpedia', 'all']:
            task = progress.add_task("Scraping FPEDIA data...", total=None)
            try:
                if force or not os.path.exists(config.GIOCATORI_CSV):
                    data_retriever.scrape_fpedia()
                    rprint("✅ [green]FPEDIA data scraped successfully[/green]")
                else:
                    rprint("ℹ️ [yellow]FPEDIA data already exists (use --force to re-download)[/yellow]")
                progress.update(task, completed=True)
            except Exception as e:
                rprint(f"❌ [red]Error scraping FPEDIA: {e}[/red]")
                
        if source in ['fstats', 'all']:
            task = progress.add_task("Fetching FSTATS data...", total=None)
            try:
                if force or not os.path.exists(config.PLAYERS_CSV):
                    data_retriever.fetch_FSTATS_data()
                    rprint("✅ [green]FSTATS data fetched successfully[/green]")
                else:
                    rprint("ℹ️ [yellow]FSTATS data already exists (use --force to re-download)[/yellow]")
                progress.update(task, completed=True)
            except Exception as e:
                rprint(f"❌ [red]Error fetching FSTATS: {e}[/red]")


@cli.command()
@click.option('--source', '-s', 
              type=click.Choice(['fpedia', 'fstats', 'all']), 
              default='all',
              help='Data source to analyze')
@click.option('--output', '-o', type=click.Path(), help='Custom output directory')
@click.option('--top', '-t', type=int, default=50, help='Show top N players in summary')
@click.pass_context
def analyze(ctx, source, output, top):
    """
    🔍 Process and analyze player data
    
    Calculates convenience indexes and generates Excel reports with
    detailed player analysis and recommendations.
    """
    verbose = ctx.obj.get('verbose', False)
    
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
        
        # Process FPEDIA
        if source in ['fpedia', 'all'] and not df_fpedia.empty:
            task = progress.add_task("Processing FPEDIA data...", total=None)
            df_processed = data_processor.process_fpedia_data(df_fpedia)
            df_final = convenienza_calculator.calcola_convenienza_fpedia(df_processed)
            
            # Save results
            output_path = os.path.join(config.OUTPUT_DIR, "fpedia_analysis.xlsx")
            df_final_sorted = df_final.sort_values(by="Convenienza Potenziale", ascending=False)
            
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
                "Ruolo",
                "Skills",
                "Buon investimento",
                "Resistenza infortuni",
                "Consigliato prossima giornata",
                "Nuovo acquisto",
                "Infortunato",
                "Squadra",
                "Trend",
                "Presenze campionato corrente",
            ]
            final_columns = [col for col in output_columns if col in df_final_sorted.columns]
            df_final_sorted[final_columns].to_excel(output_path, index=False)
            
            progress.update(task, completed=True)
            rprint(f"✅ [green]FPEDIA analysis saved to {output_path}[/green]")
            
            # Show top players
            _show_top_players(df_final_sorted, "FPEDIA", top)
        
        # Process FSTATS
        if source in ['fstats', 'all'] and not df_fstats.empty:
            task = progress.add_task("Processing FSTATS data...", total=None)
            df_processed = data_processor.process_FSTATS_data(df_fstats)
            df_final = convenienza_calculator.calcola_convenienza_FSTATS(df_processed)
            
            # Save results
            output_path = os.path.join(config.OUTPUT_DIR, "FSTATS_analysis.xlsx")
            df_final_sorted = df_final.sort_values(by="Convenienza Potenziale", ascending=False)
            
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
                "assists",
                "goals",
                "goals90min",
                "goalsFromOpenPlays",
                "xgFromOpenPlays",
                "xgFromOpenPlays/90min",
                "xA",
                "xA90min",
                "redCards",
                "yellowCards",
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
            final_columns = [col for col in output_columns if col in df_final_sorted.columns]
            df_final_sorted[final_columns].to_excel(output_path, index=False)
            
            progress.update(task, completed=True)
            rprint(f"✅ [green]FSTATS analysis saved to {output_path}[/green]")
            
            # Show top players
            _show_top_players(df_final_sorted, "FSTATS", top)


@cli.command()
@click.option('--source', '-s', 
              type=click.Choice(['fpedia', 'fstats', 'all']), 
              default='all',
              help='Data source for full pipeline')
@click.option('--force-scrape', is_flag=True, help='Force re-download of data')
@click.option('--top', '-t', type=int, default=20, help='Show top N players in summary')
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
@click.option('--source', '-s', 
              type=click.Choice(['fpedia', 'fstats']), 
              required=True,
              help='Data source to inspect')
@click.option('--role', '-r', help='Filter by player role (e.g., Portieri, Difensori)')
@click.option('--team', help='Filter by team name')
@click.option('--limit', '-l', type=int, default=10, help='Number of players to show')
def inspect(source, role, team, limit):
    """
    🔍 Inspect loaded data without full analysis
    
    Quick preview of the data to verify scraping worked correctly
    and explore player information before running analysis.
    """
    df_fpedia, df_fstats = data_processor.load_dataframes()
    
    if source == 'fpedia':
        df = df_fpedia
        if df.empty:
            rprint("❌ [red]No FPEDIA data found. Run 'fantacalcio scrape' first.[/red]")
            return
    else:
        df = df_fstats
        if df.empty:
            rprint("❌ [red]No FSTATS data found. Run 'fantacalcio scrape' first.[/red]")
            return
    
    # Apply filters
    if role and 'Ruolo' in df.columns:
        df = df[df['Ruolo'].str.contains(role, case=False, na=False)]
    
    if team and 'Squadra' in df.columns:
        df = df[df['Squadra'].str.contains(team, case=False, na=False)]
    
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
    key_cols = ['Nome', 'Ruolo', 'Squadra']
    if source == 'fpedia':
        key_cols.extend(['Punteggio', 'Presenze campionato corrente'])
    else:
        key_cols.extend(['fanta_avg', 'presences'])
    
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
    table = Table(title="Fantacalcio-PY Status", show_header=True, header_style="bold cyan")
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
        f"{fpedia_size // 1024} KB" if fpedia_exists else "Not found"
    )
    
    table.add_row(
        "FSTATS Data",
        "✅ Ready" if fstats_exists and fstats_size > 0 else "❌ Missing", 
        f"{fstats_size // 1024} KB" if fstats_exists else "Not found"
    )
    
    # Check output directory
    output_exists = os.path.exists(config.OUTPUT_DIR)
    table.add_row(
        "Output Directory",
        "✅ Ready" if output_exists else "❌ Missing",
        config.OUTPUT_DIR
    )
    
    # Check .env file
    env_exists = os.path.exists('.env')
    table.add_row(
        "Environment Config",
        "✅ Found" if env_exists else "⚠️ Missing",
        ".env file for FSTATS credentials"
    )
    
    # Configuration
    table.add_row("Current Season", "ℹ️", str(config.ANNO_CORRENTE))
    table.add_row("FSTATS Season", "ℹ️", str(config.FSTATS_ANNO))
    
    console.print(table)
    
    if not env_exists:
        rprint("\n⚠️ [yellow]Warning: .env file not found![/yellow]")
        rprint("Create a .env file with your FSTATS credentials to enable FSTATS data fetching.")


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
        convenience = row.get('Convenienza Potenziale', row.get('Convenienza', 0))
        table.add_row(
            str(idx),
            str(row.get('Nome', 'N/A')),
            str(row.get('Ruolo', 'N/A')),
            str(row.get('Squadra', 'N/A')),
            f"{convenience:.2f}" if pd.notna(convenience) else "N/A"
        )
    
    console.print(table)


if __name__ == '__main__':
    # Import pandas here to avoid circular import issues
    import pandas as pd
    cli()