import difflib, pandas as pd


def _best_match(name, candidates, cutoff=0.70):
    name_tokens = set(name.split())
    for c in candidates:
        if " " not in c and c in name_tokens:
            return c
    key = " ".join(sorted(name.split()))
    cand_sorted = {c: " ".join(sorted(c.split())) for c in candidates}
    rev = {v: k for k, v in cand_sorted.items()}
    m = difflib.get_close_matches(key, list(cand_sorted.values()), n=1, cutoff=cutoff)
    return rev[m[0]] if m else None


def merge(fp, u_prev, u_curr, ext=None):
    d_prev = {r["norm"]: r for _, r in u_prev.iterrows()}
    d_curr = {r["norm"]: r for _, r in u_curr.iterrows()}
    d_ext = {r["norm"]: r for _, r in ext.iterrows()} if ext is not None and not ext.empty else {}
    cand_prev = list(d_prev.keys())
    cand_curr = list(d_curr.keys())
    cand_ext = list(d_ext.keys())
    rows = []
    for _, r in fp.iterrows():
        n = r["norm"]
        mp = d_prev.get(n)
        if mp is None:
            bm = _best_match(n, cand_prev)
            mp = d_prev.get(bm) if bm else None
        mc = d_curr.get(n)
        if mc is None:
            bm = _best_match(n, cand_curr)
            mc = d_curr.get(bm) if bm else None
        me = d_ext.get(n)
        if me is None and cand_ext:
            bm = _best_match(n, cand_ext)
            me = d_ext.get(bm) if bm else None
        rec = dict(r)
        rec["up_team"] = mp["team_title"] if mp is not None else ""
        rec["up_games"] = mp["games"] if mp is not None else 0
        rec["up_min"] = mp["time"] if mp is not None else 0
        rec["up_goals"] = mp["goals"] if mp is not None else 0
        rec["up_xG"] = round(float(mp["xG"]), 2) if mp is not None else 0
        rec["up_xA"] = round(float(mp["xA"]), 2) if mp is not None else 0
        rec["up_assists"] = mp["assists"] if mp is not None else 0
        rec["up_kp"] = mp["key_passes"] if mp is not None else 0
        rec["up_y"] = mp["yellow_cards"] if mp is not None else 0
        rec["up_r"] = mp["red_cards"] if mp is not None else 0
        rec["uc_games"] = mc["games"] if mc is not None else 0
        rec["uc_goals"] = mc["goals"] if mc is not None else 0
        rec["uc_xG"] = round(float(mc["xG"]), 2) if mc is not None else 0
        rec["uc_xA"] = round(float(mc["xA"]), 2) if mc is not None else 0
        rec["uc_assists"] = mc["assists"] if mc is not None else 0
        rec["ext_fanta"] = me["ext_fanta"] if me is not None and pd.notna(me.get("ext_fanta")) else None
        rec["ext_tit"] = me["titolarita"] if me is not None and pd.notna(me.get("titolarita")) else None
        rec["ext_cont"] = me["continuita"] if me is not None and pd.notna(me.get("continuita")) else None
        rec["ext_mv"] = me["mv"] if me is not None and pd.notna(me.get("mv")) else None
        rec["ext_xg"] = me["ext_xg"] if me is not None else 0
        rec["ext_clean"] = me["ext_clean"] if me is not None else 0
        rows.append(rec)
    return pd.DataFrame(rows)
