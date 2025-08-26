"""
Rich utilities for enhanced progress bars and UI components
"""
import time
from contextlib import contextmanager
from typing import Iterator, Optional, Callable, Any

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    TaskID
)
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich import print as rprint
from rich.text import Text


console = Console()


class FantacalcioProgress:
    """Enhanced progress bars for Fantacalcio operations"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = None
        
    @contextmanager
    def scraping_progress(self) -> Iterator[Progress]:
        """Progress bar optimized for scraping operations"""
        with Progress(
            SpinnerColumn(spinner_style="cyan"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            refresh_per_second=10
        ) as progress:
            yield progress
    
    @contextmanager    
    def analysis_progress(self) -> Iterator[Progress]:
        """Progress bar optimized for analysis operations"""
        with Progress(
            SpinnerColumn(spinner_style="green"),
            TextColumn("[bold green]{task.description}"),
            BarColumn(bar_width=40, complete_style="green", finished_style="bright_green"),
            TaskProgressColumn(),
            console=self.console,
            refresh_per_second=5
        ) as progress:
            yield progress
    
    @contextmanager
    def simple_progress(self, description: str) -> Iterator[Callable[[str], None]]:
        """Simple spinner for operations without known total"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(description, total=None)
            
            def update_description(new_desc: str):
                progress.update(task, description=new_desc)
            
            yield update_description
            progress.update(task, completed=True)


class StatusDisplay:
    """Rich status display for application state"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def show_banner(self):
        """Display application banner"""
        banner = Panel(
            Text("🏆 FANTACALCIO-PY 🏆", style="bold blue", justify="center") +
            Text("\nAdvanced Fantasy Football Analysis Tool", style="cyan", justify="center"),
            title="Welcome",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(banner)
    
    def show_section_header(self, title: str, emoji: str = "📊"):
        """Display section header"""
        header = Panel(
            Text(f"{emoji} {title}", style="bold white", justify="center"),
            border_style="cyan",
            padding=(0, 2)
        )
        self.console.print(header)
    
    def show_data_summary(self, fpedia_count: int = 0, fstats_count: int = 0):
        """Display data loading summary"""
        table = Table(title="Data Summary", show_header=True, header_style="bold magenta")
        table.add_column("Source", style="cyan")
        table.add_column("Players", justify="right", style="green")
        table.add_column("Status", justify="center")
        
        fpedia_status = "✅ Ready" if fpedia_count > 0 else "❌ Empty"
        fstats_status = "✅ Ready" if fstats_count > 0 else "❌ Empty"
        
        table.add_row("FPEDIA", str(fpedia_count), fpedia_status)
        table.add_row("FSTATS", str(fstats_count), fstats_status)
        table.add_row("Total", str(fpedia_count + fstats_count), "📊 Combined")
        
        self.console.print(table)
    
    def show_top_players_table(self, df, source_name: str, top_n: int = 20, convenience_col: str = None):
        """Display top players in an enhanced table"""
        if df.empty:
            rprint(f"[yellow]No {source_name} data available[/yellow]")
            return
        
        # Auto-detect convenience column
        if not convenience_col:
            convenience_col = 'Convenienza Potenziale' if 'Convenienza Potenziale' in df.columns else 'Convenienza'
        
        # Create table
        table = Table(
            title=f"🏆 Top {min(top_n, len(df))} Players - {source_name}",
            show_header=True,
            header_style="bold green",
            border_style="green"
        )
        
        # Add columns with styling
        table.add_column("🏅 Rank", justify="center", style="bold yellow", width=6)
        table.add_column("👤 Name", style="bold cyan", min_width=15)
        table.add_column("⚽ Role", style="blue", width=12)
        table.add_column("🏟️ Team", style="magenta", width=10)
        table.add_column("💎 Convenience", justify="right", style="bold green", width=12)
        
        # Add additional columns based on source
        if source_name == "FPEDIA":
            if "Punteggio" in df.columns:
                table.add_column("📊 Score", justify="right", style="bright_blue", width=8)
            if "Presenze campionato corrente" in df.columns:
                table.add_column("🎯 Appearances", justify="right", style="cyan", width=12)
        else:  # FSTATS
            if "fanta_avg" in df.columns:
                table.add_column("📈 Fanta Avg", justify="right", style="bright_blue", width=10)
            if "presences" in df.columns:
                table.add_column("🎯 Presences", justify="right", style="cyan", width=10)
        
        # Add rows with color coding
        df_top = df.head(top_n)
        for idx, (_, row) in enumerate(df_top.iterrows(), 1):
            convenience = row.get(convenience_col, 0)
            
            # Color code rank
            if idx == 1:
                rank_style = "bold gold1"
                rank = "🥇 1"
            elif idx == 2:
                rank_style = "bold bright_white"
                rank = "🥈 2"
            elif idx == 3:
                rank_style = "bold color(208)"  # Bronze
                rank = "🥉 3"
            else:
                rank_style = "bold white"
                rank = str(idx)
            
            # Format convenience score with color
            if convenience > 10:
                conv_color = "bold bright_green"
            elif convenience > 5:
                conv_color = "bold green"
            elif convenience > 2:
                conv_color = "yellow"
            else:
                conv_color = "red"
            
            convenience_str = f"{convenience:.2f}" if pd.notna(convenience) else "N/A"
            
            # Base row data
            row_data = [
                Text(rank, style=rank_style),
                str(row.get('Nome', 'N/A')),
                str(row.get('Ruolo', 'N/A')),
                str(row.get('Squadra', 'N/A')),
                Text(convenience_str, style=conv_color)
            ]
            
            # Add source-specific columns
            if source_name == "FPEDIA":
                if "Punteggio" in df.columns:
                    score = row.get('Punteggio', 0)
                    row_data.append(f"{score:.1f}" if pd.notna(score) else "N/A")
                if "Presenze campionato corrente" in df.columns:
                    apps = row.get('Presenze campionato corrente', 0)
                    row_data.append(str(int(apps)) if pd.notna(apps) else "N/A")
            else:  # FSTATS
                if "fanta_avg" in df.columns:
                    fanta_avg = row.get('fanta_avg', 0)
                    row_data.append(f"{fanta_avg:.2f}" if pd.notna(fanta_avg) else "N/A")
                if "presences" in df.columns:
                    presences = row.get('presences', 0)
                    row_data.append(str(int(presences)) if pd.notna(presences) else "N/A")
            
            table.add_row(*row_data)
        
        self.console.print(table)
        
        # Show summary stats
        if len(df) > top_n:
            rprint(f"\n[dim]Showing top {top_n} of {len(df)} total players[/dim]")


def simulate_progress_task(progress: Progress, task_id: TaskID, total_steps: int, description: str):
    """Simulate a progress task for demonstration"""
    for i in range(total_steps):
        time.sleep(0.1)  # Simulate work
        progress.update(task_id, advance=1, description=f"{description} (step {i+1}/{total_steps})")


def create_layout_demo():
    """Create a demo layout showing Rich capabilities"""
    layout = Layout()
    
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    layout["header"].update(Panel("Fantacalcio-PY Dashboard", style="bold blue"))
    layout["footer"].update(Panel("Ready for action!", style="green"))
    
    # Split body into two columns
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Add content to left panel
    status_table = Table(title="System Status")
    status_table.add_column("Component")
    status_table.add_column("Status")
    status_table.add_row("Data Loader", "✅ Ready")
    status_table.add_row("Analyzer", "✅ Ready")
    status_table.add_row("Exporter", "✅ Ready")
    
    layout["left"].update(Panel(status_table, title="Status"))
    layout["right"].update(Panel("Ready to analyze!", title="Analysis"))
    
    return layout


# Import pandas for type hints
try:
    import pandas as pd
except ImportError:
    pd = None