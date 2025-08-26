# 🏆 Fantacalcio-PY CLI

## New Modern CLI Interface

Il progetto ora include una moderna interfaccia a riga di comando con funzionalità avanzate:

### 🚀 Installazione e Setup

```bash
# Install dependencies
poetry install

# CLI Usage Options:
# Option 1: Direct python module
poetry run python cli.py --help

# Option 2: Use wrapper scripts
./fantacalcio.sh --help        # Linux/Mac
fantacalcio.cmd --help         # Windows

# Option 3: Add alias (optional)
alias fantacalcio="poetry run python cli.py"
```

### 📋 Comandi Principali

#### 1. **Comando Completo**
```bash
# Esegue l'intera pipeline (scraping + analisi)
poetry run python cli.py run

# Con opzioni avanzate  
poetry run python cli.py run --source fpedia --top 30 --force-scrape
```

#### 2. **Scraping Dati**
```bash
# Scarica dati da tutte le fonti
poetry run python cli.py scrape

# Solo da una fonte specifica
poetry run python cli.py scrape --source fpedia
poetry run python cli.py scrape --source fstats

# Forza il re-download
poetry run python cli.py scrape --force
```

#### 3. **Analisi Dati**
```bash
# Analizza tutti i dati disponibili
poetry run python cli.py analyze

# Analizza solo una fonte
poetry run python cli.py analyze --source fpedia

# Mostra top 20 giocatori nel summary
poetry run python cli.py analyze --top 20

# Output personalizzato
poetry run python cli.py analyze --output ./custom_output/
```

#### 4. **Ispezione Dati**
```bash
# Visualizza preview dei dati FPEDIA
poetry run python cli.py inspect --source fpedia

# Filtra per ruolo
poetry run python cli.py inspect --source fpedia --role Attaccanti

# Filtra per squadra  
poetry run python cli.py inspect --source fstats --team Milan --limit 15
```

#### 5. **Status Sistema**
```bash
# Controlla stato dei file e configurazione
poetry run python cli.py status
```

### 🎨 Funzionalità Avanzate

#### **Progress Bars Intelligenti**
- Progress bars animate con Rich
- Indicatori di performance in tempo reale
- Stima tempi di completamento
- Gestione errori visuale

#### **Output Colorato e Tabelle**
- Tabelle formattate con evidenziazione dei migliori giocatori
- Codici colore per metriche di convenienza
- Emoji e icone per migliore UX
- Layout responsive

#### **Configurazione YAML**
```yaml
# fantacalcio.yaml
analysis:
  anno_corrente: 2025
  peso_fantamedia: 0.6
  peso_punteggio: 0.4

scraping:
  max_workers: 10
  delay_between_requests: 0.5

output:
  max_players_display: 100
  decimal_precision: 3

logging:
  level: DEBUG
  file_output: true
```

#### **Logging Strutturato**
- Log JSON per analisi avanzate
- Metriche di performance automatiche
- Tracking qualità dati
- Output Rich per sviluppo

### 🔧 Opzioni Globali

```bash
# Verbose mode per debugging
fantacalcio --verbose run

# Config file personalizzato
fantacalcio --config-file ./my-config.yaml analyze

# Combinando opzioni
fantacalcio -v -c ./prod-config.yaml run --source all
```

### 📊 Esempi di Output

#### **Top Players Table**
```
🏆 Top 20 Players - FPEDIA                                    
┌─────┬────────────────┬──────────────┬──────────┬─────────────┐
│ 🏅  │ 👤 Name        │ ⚽ Role      │ 🏟️ Team  │ 💎 Conv... │
│ Rank │                │              │          │             │
├─────┼────────────────┼──────────────┼──────────┼─────────────┤
│ 🥇 1 │ Lautaro        │ Attaccanti   │ Inter    │       15.32 │
│ 🥈 2 │ Vlahovic      │ Attaccanti   │ Juventus │       12.87 │
│ 🥉 3 │ Osimhen       │ Attaccanti   │ Napoli   │       11.45 │
└─────┴────────────────┴──────────────┴──────────┴─────────────┘
```

#### **Status Dashboard**
```
📋 Fantacalcio-PY Status
┌─────────────────┬──────────┬─────────────────────────────┐
│ Component       │  Status  │ Details                     │
├─────────────────┼──────────┼─────────────────────────────┤
│ FPEDIA Data     │ ✅ Ready │ 2847 KB                    │
│ FSTATS Data     │ ✅ Ready │ 1923 KB                    │
│ Output Dir      │ ✅ Ready │ data/output                │
│ Environment     │ ✅ Found │ .env file for FSTATS creds │
└─────────────────┴──────────┴─────────────────────────────┘
```

### 🆚 Confronto con Versione Originale

| Feature | Originale | Nuova CLI |
|---------|-----------|-----------|
| **Interface** | Script singolo | Comandi modulari |
| **Progress** | tqdm basic | Rich animated |
| **Output** | Print semplice | Tabelle colorate |
| **Config** | Hard-coded | YAML flessibile |
| **Logging** | Loguru basic | Strutturato JSON |
| **Error Handling** | Minimo | Robusto con retry |
| **UX** | Funzionale | Moderno e intuitivo |

### 🔄 Migrazione

Il vecchio `main.py` continua a funzionare, ma la nuova CLI offre:
- Migliore esperienza utente
- Configurazione flessibile  
- Migliore debugging
- Funzionalità modulari

Per utilizzare la nuova CLI, installa le dipendenze e usa `fantacalcio` invece di `python main.py`.

### 💡 Tips

1. **Usa `fantacalcio status`** per verificare tutto prima di iniziare
2. **Configura logging verbose** con `-v` per debugging
3. **Personalizza config YAML** per le tue esigenze
4. **Usa filters con `inspect`** per esplorare i dati
5. **Combina `--force-scrape`** con `--source` per aggiornamenti mirati