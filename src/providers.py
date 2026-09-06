import os, json, re, socket, requests, pandas as pd
from bs4 import BeautifulSoup
from src import config
from src.fpd import scrape_fpd
from src.utils import norm

HISTORIC_TABLES = {
    2024: ["Napoli", "Inter", "Atalanta", "Juventus", "Roma", "Fiorentina", "Lazio", "Milan", "Bologna", "Como", "Torino", "Udinese", "Genoa", "Verona", "Lecce", "Parma", "Cagliari", "Empoli", "Venezia", "Monza"],
    2025: ["Napoli", "Inter", "Atalanta", "Juventus", "Roma", "Milan", "Lazio", "Fiorentina", "Bologna", "Como", "Torino", "Udinese", "Genoa", "Lecce", "Verona", "Parma", "Cagliari", "Sassuolo", "Pisa", "Cremonese"],
}


def _weights_from_table(table):
    n = len(table)
    w = {}
    for i, team in enumerate(table):
        w[norm(team)] = round(1.15 - i * (0.30 / (n - 1)), 3)
    return w, min(w.values())


def _fanta_get(url, timeout=20):
    from dotenv import load_dotenv
    load_dotenv(".env")
    mail = os.getenv("FSTATS_MAIL")
    pwd = os.getenv("FSTATS_PASSWORD")
    if not mail or not pwd:
        return None
    r = requests.post(config.EXT_LOGIN_URL,
        json={"email": mail, "password": pwd},
        headers={"content-type": "application/json", "origin": config.EXT_ORIGIN, "referer": config.EXT_ORIGIN, "x-client-id": config.EXT_CLIENT_ID, "user-agent": "Mozilla/5.0"}, timeout=timeout)
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok:
        return None
    orig = socket.getaddrinfo

    def patched(h, p, *a, **kw):
        if h == config.EXT_API_HOST:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('188.114.96.7', p))]
        return orig(h, p, *a, **kw)

    socket.getaddrinfo = patched
    try:
        rr = requests.get(url, headers={"accept": "application/json", "authorization": f"Bearer {tok}", "origin": config.EXT_ORIGIN, "referer": config.EXT_ORIGIN, "user-agent": "Mozilla/5.0"}, timeout=timeout)
        if rr.status_code != 200:
            return None
        return rr.json()
    finally:
        socket.getaddrinfo = orig


def get_tier_weights(anno):
    """Pesi deterministici da classifica anno-1. Neopromosse = peso minimo uguale."""
    season = anno - 1
    table = None
    try:
        j = _fanta_get(config.EXT_STANDINGS_URL, timeout=10)
        if j:
            data = j.get("data", [])
            if data and max(d.get("played", 0) for d in data) >= 34:
                table = [d["team_name"] for d in sorted(data, key=lambda x: x["position"])]
    except Exception:
        pass
    if not table:
        table = HISTORIC_TABLES.get(season)
    if not table:
        return {}, 0.85
    return _weights_from_table(table)


def fetch_stats(season: int):
    cache = f"data/stats_{season}.json"
    if not os.path.exists(cache):
        league_url = f"{config.STATS_LEAGUE_URL}{season}"
        stats_url = config.STATS_PLAYERS_URL
        s = requests.Session()
        h = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Referer": league_url}
        s.get(league_url, headers=h)
        r = s.post(stats_url, headers=h, data={"league": "Serie A", "season": str(season)})
        r.raise_for_status()
        players = r.json()["players"]
        with open(cache, "w") as f:
            json.dump(players, f)
        print(f"[provider stats] {season}: {len(players)} scaricati")
    with open(cache) as f:
        df = pd.DataFrame(json.load(f))
    for c in ["games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes", "yellow_cards", "red_cards"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["norm"] = df["player_name"].map(norm)
    return df


def load_fp(force=False):
    if force:
        scrape_fpd(force=True)
    elif not os.path.exists(config.GIOCATORI_CSV):
        scrape_fpd()
    df = pd.read_csv(config.GIOCATORI_CSV)
    df["norm"] = df["Nome"].map(norm)
    return df


def fetch_provider_stats():
    """1 chiamata bulk -> indice, titolarità, continuità, MV, clean sheets. Cache data/provider_ext.json"""
    cache = "data/provider_ext.json"
    if os.path.exists(cache):
        data = json.load(open(cache))
    else:
        data = _fanta_get(config.EXT_PLAYERS_URL)
        if not data:
            print("[provider ext] credenziali mancanti o fetch fallito, skip")
            return pd.DataFrame()
        with open("data/provider_ext.json", "w") as f:
            json.dump(data, f)
        print(f"[provider ext] {len(data.get('items', []))} giocatori")
    items = data.get("items", data) if isinstance(data, dict) else data
    df = pd.DataFrame(items)
    for c in ["fanta_index", "titolarita", "continuita", "mv"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "advanced_stats" in df.columns:
        df["ext_xg"] = df["advanced_stats"].apply(lambda x: (x or {}).get("xg", 0) if isinstance(x, dict) else 0)
        df["ext_xa"] = df["advanced_stats"].apply(lambda x: (x or {}).get("xa", 0) if isinstance(x, dict) else 0)
        df["ext_clean"] = df["advanced_stats"].apply(lambda x: (x or {}).get("clean_sheet", 0) if isinstance(x, dict) else 0)
    else:
        df["ext_xg"] = 0
        df["ext_xa"] = 0
        df["ext_clean"] = 0
    df["norm"] = df["display_name"].map(norm)
    df["ext_fanta"] = df.get("fanta_index")
    return df


def fetch_infortunati():
    """Articolo infortunati -> [{squadra, voci:[{nome, dettaglio}]}]. Cache data/infortunati.json"""
    cache = "data/infortunati.json"
    if os.path.exists(cache):
        return json.load(open(cache))
    s = BeautifulSoup(requests.get(config.INF_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).content, "html.parser")
    for bad in s(["script", "style", "nav", "footer", "header", "form"]):
        bad.decompose()
    lines = [l for l in s.get_text("\n", strip=True).split("\n") if l]
    out, cur, i = [], None, 0
    while i < len(lines):
        m = re.match(r"Lista infortunati (.+)", lines[i])
        if m and "Serie A aggiornata" not in m.group(1):
            cur = {"squadra": m.group(1), "voci": []}
            out.append(cur)
        elif cur and lines[i].startswith(": ") and i > 0 and not lines[i - 1].startswith(("Lista ", "Squalificati")):
            cur["voci"].append({"nome": lines[i - 1], "dettaglio": lines[i][2:]})
        i += 1
    json.dump(out, open(cache, "w"), ensure_ascii=False)
    print(f"[infortunati] {len(out)} squadre, {sum(len(s['voci']) for s in out)} voci")
    return out


def fetch_rose(anno):
    """Rose Serie A -> [{squadra, modulo, formazione[], rigoristi[], migliori[]}]. Cache data/rose_<anno>.json"""
    cache = f"data/rose_{anno}.json"
    if os.path.exists(cache):
        return json.load(open(cache))
    h = {"User-Agent": "Mozilla/5.0"}
    idx = BeautifulSoup(requests.get(config.ROSE_INDEX_URL, headers=h, timeout=20).content, "html.parser")
    teams = []
    for a in idx.find_all("a", href=re.compile(r"/rose-serie-a/\d+/\w+")):
        if a["href"] not in [t[1] for t in teams]:
            teams.append((a.get_text(" ", strip=True)[:30], a["href"]))
    out = []
    for name, href in teams:
        try:
            s = BeautifulSoup(requests.get(href, headers=h, timeout=20).content, "html.parser")
            d = {"squadra": name, "url": href, "modulo": None, "formazione": [], "rigoristi": [], "migliori": []}
            m = re.search(r"Il modulo principale:\s*([\d-]+)", s.get_text(" ", strip=True))
            d["modulo"] = m.group(1) if m else None
            mod = s.select_one("div.row.modulo")
            if mod:
                d["formazione"] = [p.get_text(strip=True) for p in mod.select("p.label") if p.get_text(strip=True)]
            for key, words in (("rigoristi", ["rigorist"]), ("migliori", ["migliori"])):
                hh = [t for t in s.find_all(["h2", "h3"]) if any(w in t.get_text().lower() for w in words)]
                if hh:
                    box = hh[0].find_parent("div")
                    while box and len(box.find_all("a")) < 1:
                        box = box.parent
                    for a in box.find_all("a", href=re.compile(r"/lista-calciatori-serie-a/\w+/\d+/")):
                        t = a.get_text(" ", strip=True)
                        if t and t not in d[key]:
                            d[key].append(t[:60])
            out.append(d)
        except Exception as e:
            print(f"[rose] skip {href}: {e}")
    json.dump(out, open(cache, "w"), ensure_ascii=False)
    print(f"[rose] {len(out)} squadre")
    return out
