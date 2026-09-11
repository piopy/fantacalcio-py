import math
import pandas as pd
from src.merge import _best_match
from src.providers import get_tier_weights
from src.utils import norm, parse_skills, clip

SKILLS_BONUS = {"Rigorista": 4.5, "Goleador": 3.5, "Titolare": 3.0, "Buona Media": 2.5, "Piazzati": 2.5, "Assistman": 2.5, "Fuoriclasse": 2.5, "Giovane talento": 1.5, "Outsider": 1.5, "Panchinaro": -4.0, "Falloso": -2.0}


def price_for(sc, ruolo, part_mult, cred_mult):
    diff = max(0.0, sc - 45.0)
    if ruolo in ["ATT", "A"]:
        return int(clip((diff ** 1.6) / 6.0 * part_mult * cred_mult, 1, 190 * cred_mult))
    if ruolo in ["CEN", "C", "TRE", "T"]:
        return int(clip((diff ** 1.5) / 9.0 * part_mult * cred_mult, 1, 85 * cred_mult))
    if ruolo in ["DIF", "D"]:
        return int(clip((diff ** 1.4) / 12.0 * part_mult * cred_mult, 1, 45 * cred_mult))
    return int(clip((diff ** 1.3) / 14.0 * part_mult * cred_mult, 1, 40 * cred_mult))


def value_df(df, anno, list_prices=None):
    """Indice Value ufficiale (qualita-prezzo): backtest 2025-26 ~2x punti/credito vs hype.
    list_prices: dict norm(nome)->Qt.A listone pre-asta. Senza listone usa Prezzo interno (meno accurato)."""
    col_prev = f"Fantamedia anno {anno - 1}-{anno}"
    col_curr = f"Fantamedia anno {anno}-{anno + 1}"
    cred_col = next((c for c in df.columns if c.startswith("Prezzo_")), None)
    cand = list((list_prices or {}).keys())
    vals, srcs = [], []
    for _, r in df.iterrows():
        fm_prev = pd.to_numeric(r.get(col_prev), errors="coerce") or 0
        fm_curr = pd.to_numeric(r.get(col_curr), errors="coerce") or 0
        games = pd.to_numeric(r.get("up_games"), errors="coerce") or 0
        fm_known = fm_prev > 0 or fm_curr > 0
        nodata = games <= 0
        if not fm_known:
            pt = pd.to_numeric(r.get("Punteggio"), errors="coerce") or 60
            fm_ref = pt / 10.0  # qualita stimata da FP se fantamedia assente
        else:
            fm_ref = fm_prev if fm_prev > 0 else fm_curr
        avail = games / 38.0 if games > 0 else 20.0 / 38.0
        base = fm_ref * avail ** 1.5 - (r.get("up_y", 0) * 0.4 + r.get("up_r", 0) * 1.5) / max(games, 1)
        if fm_known and fm_ref < 5.5:
            base *= max(0.0, fm_ref - 4.5)  # floor: scarsi sempre in campo restano scarsi
        if not nodata and games < 8:
            base *= games / 8.0  # rampa anti una-presenza/terzi portieri
        key = norm(str(r.get("Nome", "")))
        price, src = None, "interno"
        if list_prices and list_prices.get(key, 0) > 0:
            price, src = list_prices[key], "listone"
        elif list_prices and cand:
            bm = _best_match(key, cand)
            if bm and list_prices.get(bm, 0) > 0:
                price, src = list_prices[bm], "listone"
        if price is None and cred_col:
            price = pd.to_numeric(r.get(cred_col), errors="coerce") or 1
        price = max(price or 1, 1)
        cont = pd.to_numeric(r.get("ext_cont"), errors="coerce")
        factor = 1 + 0.5 * (cont / 100.0) if pd.notna(cont) and not nodata else 1.0
        vals.append(round(max(base, 0) / math.log1p(price) * factor, 1))
        srcs.append("nodata" if nodata else src)
    df["Value"] = vals
    df["Value_src"] = srcs
    mx = max(vals) or 1
    df["Affare"] = [round(v / mx * 100, 1) for v in vals]
    return df


def score_df(df, anno, partecipanti, crediti):
    col_prev = f"Fantamedia anno {anno - 1}-{anno}"
    col_curr = f"Fantamedia anno {anno}-{anno + 1}"
    part_mult = {8: 0.85, 10: 1.0, 12: 1.18}.get(partecipanti, 0.85 + (partecipanti - 8) * 0.07)
    cred_mult = crediti / 500.0
    w_map, w_min = get_tier_weights(anno)
    scores = []
    prezzi = []
    gems = []
    reasons = []
    for _, r in df.iterrows():
        ruolo = str(r.get("Ruolo", "CEN")).upper()
        fm_prev = pd.to_numeric(r.get(col_prev), errors="coerce") or 0
        fm_curr = pd.to_numeric(r.get(col_curr), errors="coerce") or 0
        pt = pd.to_numeric(r.get("ext_fanta"), errors="coerce")
        pt = pt if pd.notna(pt) and pt > 0 else pd.to_numeric(r.get("Punteggio"), errors="coerce") or 50
        xg = r.get("up_xG", 0)
        xa = r.get("up_xA", 0)
        g = r.get("up_goals", 0)
        a = r.get("up_assists", 0)
        kp = r.get("up_kp", 0)
        games = r.get("up_games", 0)
        mins = r.get("up_min", 0)
        base = pt * 0.35
        fm_ref = fm_prev if fm_prev > 0 else (fm_curr if fm_curr > 0 else 6.0)
        fm_score = clip((fm_ref - 5.0) / 3.5 * 30, 0, 30)
        p90 = (90.0 / mins) if mins >= 450 else 0.1
        xg_p90 = xg * p90 if mins >= 450 else xg / max(games, 1)
        xa_p90 = xa * p90 if mins >= 450 else xa / max(games, 1)
        if ruolo in ["ATT", "A"]:
            xt = clip(xg_p90 * 25 + xa_p90 * 15, 0, 20)
        elif ruolo in ["CEN", "C", "TRE", "T"]:
            xt = clip(xg_p90 * 20 + xa_p90 * 25 + (kp / max(games, 1)) * 3, 0, 20)
        elif ruolo in ["DIF", "D"]:
            xt = clip(xg_p90 * 15 + xa_p90 * 20, 0, 15)
        else:
            xt = 10.0 if "Titolare" in str(r.get("Skills")) else 4.0
        sk = sum(SKILLS_BONUS.get(s, 0) for s in parse_skills(r.get("Skills", [])))
        if r.get("Infortunato") is True:
            sk -= 4
        if r.get("Trend") == "UP":
            sk += 1.5
        sk_score = clip(sk + 5, 0, 15)
        disc = clip((r.get("up_y", 0) * 0.4 + r.get("up_r", 0) * 1.5) / max(games, 1) * 5, 0, 5)
        raw = base + fm_score + xt + sk_score - disc
        tit = r.get("ext_tit")
        cont = r.get("ext_cont")
        if pd.notna(tit):
            raw += clip((tit - 50) / 50 * 3, -2, 3)
        if pd.notna(cont):
            raw += clip((cont - 50) / 50 * 2, -1, 2)
        if r.get("up_team") and str(r["up_team"]) != str(r.get("Squadra")):
            w_new = w_map.get(norm(str(r.get("Squadra"))), w_min)
            w_old = w_map.get(norm(str(r["up_team"])), w_min)
            if ruolo in ["POR", "P", "DIF", "D"]:
                mult = (w_new / w_old) ** 0.5
            else:
                if pd.notna(tit) and tit >= 70 and w_new < w_old:
                    mult = (w_old / w_new) ** 0.25
                else:
                    mult = (w_new / w_old) ** 0.25
            raw *= mult
        sc = round(clip(raw, 1, 99), 1)
        scores.append(sc)
        pr = price_for(sc, ruolo, part_mult, cred_mult)
        prezzi.append(pr)
        rs = []
        if xg - g >= 2:
            rs.append(f"xG non capitalizzati (+{round(xg - g, 1)})")
        if xa - a >= 2:
            rs.append(f"xA sprecati (+{round(xa - a, 1)})")
        if xg_p90 + xa_p90 > 0.35 and pr <= 20 and ruolo != "ATT":
            rs.append("Volume elite per ruolo")
        if rs and sc >= 60:
            gems.append("SÌ")
            reasons.append(" | ".join(rs))
        else:
            gems.append("NO")
            reasons.append("-" if not rs else " | ".join(rs) if sc < 60 else "-")
    df["Punteggio_Asta_100"] = scores
    df[f"Prezzo_{crediti}"] = prezzi
    df["Hidden_Gem"] = gems
    df["Motivo_Hidden_Gem"] = reasons
    df["_cred_col"] = f"Prezzo_{crediti}"
    return df


def alternatives(df, cred_col):
    alts = []
    for _, r in df.iterrows():
        cands = df[(df["Ruolo"] == r["Ruolo"]) & (df["Nome"] != r["Nome"])].copy()
        if cands.empty:
            alts.append("-")
            continue
        cands["d"] = (cands["Punteggio_Asta_100"] - r["Punteggio_Asta_100"]).abs() + (cands["Squadra"] == r["Squadra"]) * 3 + (cands["up_xG"] - r.get("up_xG", 0)).abs() * 0.5
        top = cands.nsmallest(3, "d")
        alts.append(", ".join(f"{x['Nome']} ({x['Squadra']}, {x['Punteggio_Asta_100']}, ~{x[cred_col]}cr)" for _, x in top.iterrows()))
    df["Alternative_Consigliate"] = alts
    return df
