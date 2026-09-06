#!/usr/bin/env python3
"""Fantacalcio-py TUI — menu interattivo sopra pipeline.py + src/*. Zero flag da ricordare."""
import glob
import json
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

console = Console()


def _ask_int(msg, default):
    try:
        return IntPrompt.ask(msg, default=default, console=console)
    except (KeyboardInterrupt, EOFError):
        return default


def cmd_run():
    anno = _ask_int("Anno", 2026)
    part = _ask_int("Partecipanti", 10)
    cred = _ask_int("Crediti", 500)
    force = Confirm.ask("Forza re-scrape?", default=False)
    no_ext = Confirm.ask("Salta provider esterno?", default=False)
    argv = ["pipeline.py", "--anno", str(anno), "--partecipanti", str(part), "--crediti", str(cred)]
    if force:
        argv.append("--force")
    if no_ext:
        argv.append("--no-ext")
    sys.argv = argv
    import pipeline
    pipeline.main()


def _age(path):
    from datetime import datetime
    if not os.path.exists(path):
        return None
    dt = datetime.fromtimestamp(os.path.getmtime(path))
    kb = os.path.getsize(path) // 1024
    return f"{dt:%Y-%m-%d %H:%M} ({kb} KB)"


def cmd_status():
    t = Table(title="Stato pipeline", show_header=True)
    t.add_column("File")
    t.add_column("Info")
    files = {
        "Cache FPD": "data/_giocatori.csv",
        "Cache stats prev": "data/stats_2025.json",
        "Cache stats live": "data/stats_2026.json",
        "Cache provider ext": "data/provider_ext.json",
        "Cache infortunati": "data/infortunati.json",
        "Cache rose": "data/rose_2026.json",
    }
    for label, path in files.items():
        t.add_row(label, _age(path) or "mancante")
    outs = sorted(glob.glob("data/output/fantacalcio_asta_*.json"))
    for o in outs[-5:]:
        t.add_row("Output", f"{os.path.basename(o)} — {_age(o)}")
    t.add_row(".env provider", "presente" if os.path.exists(".env") else "mancante (usa --no-ext / skip ext)")
    console.print(t)


def _latest_output():
    outs = sorted(glob.glob("data/output/fantacalcio_asta_*.json"))
    return outs[-1] if outs else None


def cmd_inspect():
    path = _latest_output()
    if not path:
        console.print("[red]Nessun output: lancia prima Run pipeline[/red]")
        return
    data = json.load(open(path, encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("players", [])
    ruolo = console.input("Filtro ruolo (invio=tutti): ").strip().upper()
    squadra = console.input("Filtro squadra (invio=tutte): ").strip().lower()
    top = _ask_int("Quanti", 20)
    if ruolo:
        rows = [r for r in rows if str(r.get("Ruolo", "")).upper().startswith(ruolo)]
    if squadra:
        rows = [r for r in rows if squadra in str(r.get("Squadra Attuale (2026-2027)", r.get("Squadra", ""))).lower()]
    price = next((k for k in (rows[0] if rows else {}) if k.startswith("Prezzo_")), "")
    t = Table(title=f"{os.path.basename(path)} — {len(rows)} gioc", show_header=True)
    for c in ["Calciatore", "Ruolo", "Punteggio Asta (/100)", price, "Gol 25-26", "xG 25-26"]:
        if c:
            t.add_column(c)
    for r in rows[:top]:
        t.add_row(*[str(r.get(c, "—")) for c in ["Calciatore", "Ruolo", "Punteggio Asta (/100)", price, "Gol 25-26", "xG 25-26"] if c])
    console.print(t)


MENU = [
    ("1", "Run pipeline", cmd_run),
    ("2", "Status cache + output", cmd_status),
    ("3", "Inspect ultimo output", cmd_inspect),
    ("0", "Esci", None),
]


def main():
    while True:
        console.print(Panel("\n".join(f"[bold]{k}[/bold] — {label}" for k, label, _ in MENU), title="Fantacalcio-py"))
        try:
            choice = console.input("Scelta: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        hit = [fn for k, _, fn in MENU if k == choice]
        if not hit:
            continue
        if hit[0] is None:
            break
        try:
            hit[0]()
        except Exception as e:
            console.print(f"[red]Errore: {e}[/red]")


if __name__ == "__main__":
    main()
