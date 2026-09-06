# pipeline.py — nuovo main. python pipeline.py --anno 2026 --partecipanti 10 --crediti 500
import argparse, json, os, pandas as pd
from src.providers import fetch_stats, load_fp, fetch_provider_stats, fetch_infortunati, fetch_rose, load_listone
from src.merge import merge
from src.scoring import score_df, value_df, alternatives


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--anno", type=int, default=2026)
    p.add_argument("--partecipanti", type=int, default=10)
    p.add_argument("--crediti", type=int, default=500)
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-ext", action="store_true", help="skip provider esterno")
    p.add_argument("--listone", default="", help="xlsx listone pre-asta (Qt.A) per indice Value")
    args = p.parse_args()
    fp = load_fp(force=args.force)
    u_prev = fetch_stats(args.anno - 1)
    u_curr = fetch_stats(args.anno)
    ext = pd.DataFrame() if args.no_ext else fetch_provider_stats()
    inf = [] if args.no_ext else fetch_infortunati()
    rose = [] if args.no_ext else fetch_rose(args.anno)
    lp = load_listone(args.listone) if args.listone else None
    if not lp:
        print("[value] NESSUN listone: denominatore = prezzo interno, accuratezza minore (vedi README)")
    df = merge(fp, u_prev, u_curr, ext, inf)
    df = score_df(df, args.anno, args.partecipanti, args.crediti)
    df = value_df(df, args.anno, lp)
    df = alternatives(df, df["_cred_col"].iloc[0])
    df.drop(columns=["_cred_col"], inplace=True)
    cred_col = f"Prezzo_{args.crediti}"
    yy_prev = f"{str(args.anno - 1)[-2:]}-{str(args.anno)[-2:]}"
    yy_curr = f"{str(args.anno)[-2:]}-{str(args.anno + 1)[-2:]}"
    out = f"data/output/fantacalcio_asta_{args.anno}_{args.anno + 1}_{args.partecipanti}p_{args.crediti}cr.xlsx"
    os.makedirs("data/output", exist_ok=True)
    cols = {"Nome": "Calciatore", "Squadra": f"Squadra Attuale ({args.anno}-{args.anno + 1})", "Ruolo": "Ruolo", "Affare": "Affare FPY", "Value_src": "Fonte Value", "Punteggio_Asta_100": "Score FPY", cred_col: cred_col, "Hidden_Gem": "Hidden Gem?", "Motivo_Hidden_Gem": "Motivo", "Alternative_Consigliate": "Alternative Affini", f"Fantamedia anno {args.anno - 1}-{args.anno}": "Fantamedia Prev", f"Fantamedia anno {args.anno}-{args.anno + 1}": "Fantamedia Live", "up_team": f"Squadra {args.anno - 1}-{args.anno}", "up_games": f"Pres {yy_prev}", "up_goals": f"Gol {yy_prev}", "up_xG": f"xG {yy_prev}", "up_assists": f"Assist {yy_prev}", "up_xA": f"xA {yy_prev}", "uc_games": f"Pres {yy_curr}", "uc_goals": f"Gol {yy_curr}", "uc_xG": f"xG {yy_curr}", "uc_assists": f"Assist {yy_curr}", "uc_xA": f"xA {yy_curr}", "Skills": "Skills", "Infortunato": "Infortunato", "Dettaglio_infortunio": "Dettaglio infortunio", "Trend": "Trend", "Consigliato prossima giornata": "Consigliato", "Buon investimento": "Buon invest.", "Resistenza infortuni": "Resist. infort.", "Gol previsti": "Gol prev.", "Assist previsti": "Assist prev.", "Eta": "Età", "Nazionalita": "Nazionalità", "Consiglio_anno": "Consiglio rif.", "Consiglio_testo": "Consiglio", "Forma_serie": "Forma serie", "Forma_media": "Forma media", "Simili": "Simili", "ext_fanta": "Indice Esterno", "ext_tit": "Titolarità", "ext_cont": "Continuità", "ext_mv": "MV Fonte Est."}
    df2 = df[[c for c in cols if c in df.columns]].rename(columns=cols).sort_values("Affare FPY", ascending=False)
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df2.to_excel(w, sheet_name="Masterlist", index=False)
        df2[df2["Hidden Gem?"] == "SÌ"].to_excel(w, sheet_name="Hidden_Gems", index=False)
        for ruolo in ["POR", "DIF", "CEN", "ATT"]:
            df_r = df2[df2["Ruolo"].str.startswith(ruolo, na=False)]
            if not df_r.empty:
                df_r.to_excel(w, sheet_name=f"Ruolo_{ruolo}", index=False)
        df2.sort_values(f"Squadra Attuale ({args.anno}-{args.anno + 1})").to_excel(w, sheet_name="Per_Squadra", index=False)
    jout = os.path.splitext(out)[0] + ".json"
    with open(jout, "w", encoding="utf-8") as f:
        json.dump({"meta": {"anno": args.anno, "partecipanti": args.partecipanti, "crediti": args.crediti,
                             "listone": bool(lp),
                             "giocatori": len(df2), "gem": int((df2["Hidden Gem?"] == "SÌ").sum())},
                   "players": df2.fillna("").to_dict("records"), "rose": rose}, f, ensure_ascii=False)
    print(f"OK {out} + {jout} — {len(df2)} gioc, {len(df2[df2['Hidden Gem?'] == 'SÌ'])} gem")


if __name__ == "__main__":
    main()
