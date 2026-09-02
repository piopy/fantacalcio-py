# pipeline.py — python pipeline.py --anno 2026 --partecipanti 10 --crediti 500
import argparse, os, re, json, ast, unicodedata, difflib, socket, requests, pandas as pd
import config, data_retriever

SKILLS_BONUS = {"Rigorista":4.5,"Goleador":3.5,"Titolare":3.0,"Buona Media":2.5,"Piazzati":2.5,"Assistman":2.5,"Fuoriclasse":2.5,"Giovane talento":1.5,"Outsider":1.5,"Panchinaro":-4.0,"Falloso":-2.0}

# Classifiche storiche per fallback deterministico (pos 1 = scudetto)
HISTORIC_TABLES = {
    2024: ["Napoli","Inter","Atalanta","Juventus","Roma","Fiorentina","Lazio","Milan","Bologna","Como","Torino","Udinese","Genoa","Verona","Lecce","Parma","Cagliari","Empoli","Venezia","Monza"],
    2025: ["Napoli","Inter","Atalanta","Juventus","Roma","Milan","Lazio","Fiorentina","Bologna","Como","Torino","Udinese","Genoa","Lecce","Verona","Parma","Cagliari","Sassuolo","Pisa","Cremonese"],
}

def _weights_from_table(table):
    # pos1 -> 1.15, pos20 -> 0.85, lineare; neopromosse assenti -> peso minimo (stesso per tutte)
    n=len(table)
    w={}
    for i, team in enumerate(table):
        # normalizza nomi per match (Milan vs AC Milan)
        w[norm(team)] = round(1.15 - i*(0.30/(n-1)), 3)
    return w, min(w.values())

def get_tier_weights(anno):
    """Pesi deterministici da classifica anno-1. Neopromosse = peso minimo uguale."""
    season = anno-1
    table = None
    # prova fetch live standings se stagione completa (played>=34)
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
        mail=os.getenv("FSTATS_MAIL"); pwd=os.getenv("FSTATS_PASSWORD")
        if mail and pwd:
            # login rapido (cache token 1h)
            import socket as _s
            orig=_s.getaddrinfo
            def patched(h,p,*a,**kw):
                if h=="api.fantagoat.it": return [(_s.AF_INET,_s.SOCK_STREAM,6,'',('188.114.96.7',p))]
                return orig(h,p,*a,**kw)
            _s.getaddrinfo=patched
            try:
                r=requests.post("https://h3ppxirqsg.execute-api.us-east-2.amazonaws.com/prod/auth/email/login",
                    json={"email":mail,"password":pwd},
                    headers={"content-type":"application/json","origin":"https://app.fantagoat.it","referer":"https://app.fantagoat.it/","x-client-id":"fantagoat-app","user-agent":"Mozilla/5.0"}, timeout=10)
                tok=r.json().get("access_token")
                if tok:
                    rr=requests.get("https://api.fantagoat.it/v1/standings", headers={"accept":"application/json","authorization":f"Bearer {tok}","origin":"https://app.fantagoat.it","referer":"https://app.fantagoat.it/","user-agent":"Mozilla/5.0"}, timeout=10)
                    if rr.status_code==200:
                        j=rr.json()
                        data=j.get("data",[])
                        # se stagione completa, usala
                        if data and max(d.get("played",0) for d in data) >= 34:
                            table=[d["team_name"] for d in sorted(data, key=lambda x: x["position"])]
            finally:
                _s.getaddrinfo=orig
    except: pass
    if not table:
        table = HISTORIC_TABLES.get(season)
    if not table:
        # fallback generico: nessuna classifica -> pesi neutri
        return {}, 0.85
    w, w_min = _weights_from_table(table)
    return w, w_min

def norm(s):
    t=re.sub(r"\s+"," ", re.sub(r"[^a-z0-9 ]"," ", unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower())).strip()
    # alias: AC Milan == Milan
    if t=="ac milan": t="milan"
    return t
def parse_skills(s):
    if isinstance(s,list): return s
    if not isinstance(s,str) or not s: return []
    try: return ast.literal_eval(s)
    except: return [x.strip(" '\"[]") for x in s.split(",") if x.strip(" '\"[]")]
def clip(v, lo, hi): return lo if v<lo else hi if v>hi else v

def fetch_understat(season: int):
    cache=f"data/understat_{season}.json"
    if not os.path.exists(cache):
        base=config.decode("aHR0cHM6Ly91bmRlcnN0YXQuY29t")
        league_url=f"{config.decode('aHR0cHM6Ly91bmRlcnN0YXQuY29tL2xlYWd1ZS9TZXJpZV9BLw==')}{season}"
        stats_url=config.decode("aHR0cHM6Ly91bmRlcnN0YXQuY29tL21haW4vZ2V0UGxheWVyc1N0YXRzLw==")
        s=requests.Session(); h={"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest","Referer":league_url}
        s.get(league_url,headers=h)
        r=s.post(stats_url,headers=h,data={"league":"Serie A","season":str(season)}); r.raise_for_status()
        players=r.json()["players"]
        with open(cache,"w") as f: json.dump(players,f)
        print(f"[provider stats] {season}: {len(players)} scaricati")
    with open(cache) as f: df=pd.DataFrame(json.load(f))
    for c in ["games","time","goals","xG","assists","xA","shots","key_passes","yellow_cards","red_cards"]:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    df["norm"]=df["player_name"].map(norm)
    return df

def load_fp(force=False):
    if force: data_retriever.scrape_fpedia(force=True)
    elif not os.path.exists(config.GIOCATORI_CSV): data_retriever.scrape_fpedia()
    df=pd.read_csv(config.GIOCATORI_CSV); df["norm"]=df["Nome"].map(norm); return df

def fetch_provider_stats():
    """1 chiamata bulk -> indice, titolarità, continuità, MV, clean sheets. Cache data/provider_ext.json"""
    cache="data/provider_ext.json"
    if os.path.exists(cache):
        data=json.load(open(cache))
    else:
        from dotenv import load_dotenv
        load_dotenv(".env")
        mail=os.getenv("FSTATS_MAIL"); pwd=os.getenv("FSTATS_PASSWORD")
        if not mail or not pwd:
            print("[provider ext] credenziali mancanti, skip")
            return pd.DataFrame()
        # endpoint login + api offuscati via base64 in config
        login_url=config.decode("aHR0cHM6Ly9oM3BweGlycXNnLmV4ZWN1dGUtYXBpLnVzLWVhc3QtMi5hbWF6b25hd3MuY29tL3Byb2QvYXV0aC9lbWFpbC9sb2dpbg==")
        api_url=config.decode("aHR0cHM6Ly9hcGkuZmFudGFnb2F0Lml0L3YxL3BsYXllcnM=")
        origin=config.decode("aHR0cHM6Ly9hcHAuZmFudGFnb2F0Lml0Lw==")
        r=requests.post(login_url,
            json={"email":mail,"password":pwd},
            headers={"content-type":"application/json","origin":origin,"referer":origin,"x-client-id":config.decode("ZmFudGFnb2F0LWFwcA=="),"user-agent":"Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        tok=r.json()["access_token"]
        orig=socket.getaddrinfo
        def patched(h,p,*a,**kw):
            if h==config.decode("YXBpLmZhbnRhZ29hdC5pdA=="): return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('188.114.96.7',p))]
            return orig(h,p,*a,**kw)
        socket.getaddrinfo=patched
        try:
            rr=requests.get(api_url,
                headers={"accept":"application/json","authorization":f"Bearer {tok}","origin":origin,"referer":origin,"user-agent":"Mozilla/5.0"}, timeout=20)
            rr.raise_for_status()
            data=rr.json()
            with open("data/provider_ext.json","w") as f: json.dump(data,f)
        finally:
            socket.getaddrinfo=orig
        print(f"[provider ext] {len(data.get('items',[]))} giocatori")
    items=data.get("items",data) if isinstance(data,dict) else data
    df=pd.DataFrame(items)
    for c in ["fanta_index","titolarita","continuita","mv"]:
        if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce")
    if "advanced_stats" in df.columns:
        df["ext_xg"]=df["advanced_stats"].apply(lambda x: (x or {}).get("xg",0) if isinstance(x,dict) else 0)
        df["ext_xa"]=df["advanced_stats"].apply(lambda x: (x or {}).get("xa",0) if isinstance(x,dict) else 0)
        df["ext_clean"]=df["advanced_stats"].apply(lambda x: (x or {}).get("clean_sheet",0) if isinstance(x,dict) else 0)
    else:
        df["ext_xg"]=0; df["ext_xa"]=0; df["ext_clean"]=0
    df["norm"]=df["display_name"].map(norm)
    df["ext_fanta"]=df.get("fanta_index")
    return df

def _best_match(name, candidates, cutoff=0.70):
    # token_sort + alias cognome singolo
    # se candidate è singolo cognome contenuto in name, match diretto
    name_tokens=set(name.split())
    for c in candidates:
        if " " not in c and c in name_tokens:
            return c
    key=" ".join(sorted(name.split()))
    cand_sorted={c:" ".join(sorted(c.split())) for c in candidates}
    rev={v:k for k,v in cand_sorted.items()}
    m=difflib.get_close_matches(key, list(cand_sorted.values()), n=1, cutoff=cutoff)
    return rev[m[0]] if m else None

def merge(fp, u_prev, u_curr, ext=None):
    d_prev={r["norm"]:r for _,r in u_prev.iterrows()}; d_curr={r["norm"]:r for _,r in u_curr.iterrows()}
    cand_prev=list(d_prev.keys()); cand_curr=list(d_curr.keys())
    d_ext={r["norm"]:r for _,r in ext.iterrows()} if ext is not None and not ext.empty else {}
    cand_ext=list(d_ext.keys())
    rows=[]
    for _,r in fp.iterrows():
        n=r["norm"]
        mp=d_prev.get(n); 
        if not mp: bm=_best_match(n,cand_prev); mp=d_prev.get(bm) if bm else None
        mc=d_curr.get(n);
        if not mc: bm=_best_match(n,cand_curr); mc=d_curr.get(bm) if bm else None
        me=d_ext.get(n);
        if not me and cand_ext: bm=_best_match(n,cand_ext); me=d_ext.get(bm) if bm else None
        rec=dict(r)
        rec["up_team"]=mp["team_title"] if mp is not None else ""
        rec["up_games"]=mp["games"] if mp is not None else 0; rec["up_min"]=mp["time"] if mp is not None else 0
        rec["up_goals"]=mp["goals"] if mp is not None else 0; rec["up_xG"]=round(float(mp["xG"]),2) if mp is not None else 0
        rec["up_xA"]=round(float(mp["xA"]),2) if mp is not None else 0; rec["up_assists"]=mp["assists"] if mp is not None else 0
        rec["up_kp"]=mp["key_passes"] if mp is not None else 0; rec["up_y"]=mp["yellow_cards"] if mp is not None else 0; rec["up_r"]=mp["red_cards"] if mp is not None else 0
        rec["uc_games"]=mc["games"] if mc is not None else 0; rec["uc_goals"]=mc["goals"] if mc is not None else 0
        rec["uc_xG"]=round(float(mc["xG"]),2) if mc is not None else 0; rec["uc_xA"]=round(float(mc["xA"]),2) if mc is not None else 0; rec["uc_assists"]=mc["assists"] if mc is not None else 0
        rec["ext_fanta"]=me["ext_fanta"] if me is not None and pd.notna(me.get("ext_fanta")) else None
        rec["ext_tit"]=me["titolarita"] if me is not None and pd.notna(me.get("titolarita")) else None
        rec["ext_cont"]=me["continuita"] if me is not None and pd.notna(me.get("continuita")) else None
        rec["ext_mv"]=me["mv"] if me is not None and pd.notna(me.get("mv")) else None
        rec["ext_xg"]=me["ext_xg"] if me is not None else 0
        rec["ext_clean"]=me["ext_clean"] if me is not None else 0
        rows.append(rec)
    return pd.DataFrame(rows)

def score_df(df, anno, partecipanti, crediti):
    col_prev=f"Fantamedia anno {anno-1}-{anno}"; col_curr=f"Fantamedia anno {anno}-{anno+1}"
    part_mult={8:0.85,10:1.0,12:1.18}.get(partecipanti,0.85+(partecipanti-8)*0.07); cred_mult=crediti/500.0
    w_map, w_min = get_tier_weights(anno)
    scores=[]; tiers=[]; prezzi=[]; gems=[]; reasons=[]
    for _,r in df.iterrows():
        ruolo=str(r.get("Ruolo","CEN")).upper()
        fm_prev=pd.to_numeric(r.get(col_prev),errors="coerce") or 0; fm_curr=pd.to_numeric(r.get(col_curr),errors="coerce") or 0
        pt=pd.to_numeric(r.get("ext_fanta"),errors="coerce")
        pt=pt if pd.notna(pt) and pt>0 else pd.to_numeric(r.get("Punteggio"),errors="coerce") or 50
        xg=r.get("up_xG",0); xa=r.get("up_xA",0); g=r.get("up_goals",0); a=r.get("up_assists",0); kp=r.get("up_kp",0); games=r.get("up_games",0); mins=r.get("up_min",0)
        base=pt*0.35; fm_ref=fm_prev if fm_prev>0 else (fm_curr if fm_curr>0 else 6.0); fm_score=clip((fm_ref-5.0)/3.5*30,0,30)
        p90=(90.0/mins) if mins>=450 else 0.1; xg_p90=xg*p90 if mins>=450 else xg/max(games,1); xa_p90=xa*p90 if mins>=450 else xa/max(games,1)
        if ruolo in ["ATT","A"]: xt=clip(xg_p90*25+xa_p90*15,0,20)
        elif ruolo in ["CEN","C","TRE","T"]: xt=clip(xg_p90*20+xa_p90*25+(kp/max(games,1))*3,0,20)
        elif ruolo in ["DIF","D"]: xt=clip(xg_p90*15+xa_p90*20,0,15)
        else: xt=10.0 if "Titolare" in str(r.get("Skills")) else 4.0
        sk=sum(SKILLS_BONUS.get(s,0) for s in parse_skills(r.get("Skills",[])))
        if r.get("Infortunato") is True: sk-=4
        if r.get("Trend")=="UP": sk+=1.5
        sk_score=clip(sk+5,0,15); disc=clip((r.get("up_y",0)*0.4+r.get("up_r",0)*1.5)/max(games,1)*5,0,5)
        raw=base+fm_score+xt+sk_score-disc
        tit=r.get("ext_tit"); cont=r.get("ext_cont")
        if pd.notna(tit): raw+=clip((tit-50)/50*3, -2, 3)
        if pd.notna(cont): raw+=clip((cont-50)/50*2, -1, 2)
        if r.get("up_team") and str(r["up_team"])!=str(r.get("Squadra")):
            w_new=w_map.get(norm(str(r.get("Squadra"))), w_min)
            w_old=w_map.get(norm(str(r["up_team"])), w_min)
            # POR/DIF: squadra forte = boost (clean sheet), ATT/CEN: effetto dimezzato, se diventa titolare inverte
            if ruolo in ["POR","P"]:
                exp=0.5
                mult=(w_new/w_old)**exp
            elif ruolo in ["DIF","D"]:
                exp=0.5
                mult=(w_new/w_old)**exp
            else:
                # CEN/ATT: dimezzato, e se titolarità sale >70 e scende di livello -> boost da protagonismo
                if pd.notna(tit) and tit>=70 and w_new < w_old:
                    mult=(w_old/w_new)**0.25  # inverte: debole ma titolare = boost
                else:
                    mult=(w_new/w_old)**0.25
            raw*=mult
        sc=round(clip(raw,1,99),1); scores.append(sc)
        diff=max(0.0,sc-45.0)
        if ruolo in ["ATT","A"]: pr=int(clip((diff**1.6)/6.0*part_mult*cred_mult,1,190*cred_mult))
        elif ruolo in ["CEN","C","TRE","T"]: pr=int(clip((diff**1.5)/9.0*part_mult*cred_mult,1,85*cred_mult))
        elif ruolo in ["DIF","D"]: pr=int(clip((diff**1.4)/12.0*part_mult*cred_mult,1,45*cred_mult))
        else: pr=int(clip((diff**1.3)/14.0*part_mult*cred_mult,1,40*cred_mult))
        prezzi.append(pr); tiers.append("1° Top" if sc>=85 else "2° Semitop" if sc>=75 else "3° Titolare" if sc>=65 else "5° Copertura" if sc>=55 else "Scommessa")
        rs=[]
        if xg-g>=2: rs.append(f"xG non capitalizzati (+{round(xg-g,1)})")
        if xa-a>=2: rs.append(f"xA sprecati (+{round(xa-a,1)})")
        if xg_p90+xa_p90>0.35 and pr<=20 and ruolo!="ATT": rs.append("Volume elite per ruolo")
        if rs and sc>=60: gems.append("SÌ"); reasons.append(" | ".join(rs))
        else: gems.append("NO"); reasons.append("-" if not rs else " | ".join(rs) if sc<60 else "-")
    df["Punteggio_Asta_100"]=scores; df["Tier"]=tiers; df[f"Prezzo_{crediti}"]=prezzi; df["Hidden_Gem"]=gems; df["Motivo_Hidden_Gem"]=reasons; df["_cred_col"]=f"Prezzo_{crediti}"
    return df

def alternatives(df, cred_col):
    alts=[]
    for _,r in df.iterrows():
        cands=df[(df["Ruolo"]==r["Ruolo"]) & (df["Nome"]!=r["Nome"])].copy()
        if cands.empty: alts.append("-"); continue
        cands["d"]=(cands["Punteggio_Asta_100"]-r["Punteggio_Asta_100"]).abs()+(cands["Squadra"]==r["Squadra"])*3+(cands["up_xG"]-r.get("up_xG",0)).abs()*0.5
        top=cands.nsmallest(3,"d")
        alts.append(", ".join(f"{x['Nome']} ({x['Squadra']}, {x['Punteggio_Asta_100']}, ~{x[cred_col]}cr)" for _,x in top.iterrows()))
    df["Alternative_Consigliate"]=alts; return df

def main():
    p=argparse.ArgumentParser(); p.add_argument("--anno",type=int,default=2026); p.add_argument("--partecipanti",type=int,default=10); p.add_argument("--crediti",type=int,default=500); p.add_argument("--force",action="store_true"); p.add_argument("--no-ext",action="store_true", help="skip provider esterno")
    args=p.parse_args()
    fp=load_fp(force=args.force); u_prev=fetch_understat(args.anno-1); u_curr=fetch_understat(args.anno); ext=pd.DataFrame() if args.no_ext else fetch_provider_stats()
    df=merge(fp,u_prev,u_curr,ext); df=score_df(df,args.anno,args.partecipanti,args.crediti); df=alternatives(df,df["_cred_col"].iloc[0]); df.drop(columns=["_cred_col"],inplace=True)
    cred_col=f"Prezzo_{args.crediti}"; out=f"data/output/fantacalcio_asta_{args.anno}_{args.anno+1}_{args.partecipanti}p_{args.crediti}cr.xlsx"; os.makedirs("data/output",exist_ok=True)
    cols={"Nome":"Calciatore","Squadra":f"Squadra Attuale ({args.anno}-{args.anno+1})","Ruolo":"Ruolo","Punteggio_Asta_100":"Punteggio Asta (/100)","Tier":"Fascia",cred_col:cred_col,"Hidden_Gem":"Hidden Gem?","Motivo_Hidden_Gem":"Motivo","Alternative_Consigliate":"Alternative Affini",f"Fantamedia anno {args.anno-1}-{args.anno}":"Fantamedia Prev",f"Fantamedia anno {args.anno}-{args.anno+1}":"Fantamedia Live","up_team":f"Squadra {args.anno-1}-{args.anno}","up_games":"Pres 25-26","up_goals":"Gol","up_xG":"xG","up_assists":"Assist","up_xA":"xA","Skills":"Skills","ext_fanta":"Indice Esterno","ext_tit":"Titolarità","ext_cont":"Continuità","ext_mv":"MV Fonte Est."}
    df2=df[[c for c in cols if c in df.columns]].rename(columns=cols).sort_values("Punteggio Asta (/100)",ascending=False)
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df2.to_excel(w, sheet_name="Masterlist", index=False)
        df2[df2["Hidden Gem?"]=="SÌ"].to_excel(w, sheet_name="Hidden_Gems", index=False)
        for ruolo in ["POR","DIF","CEN","ATT"]:
            df_r=df2[df2["Ruolo"].str.startswith(ruolo,na=False)]
            if not df_r.empty: df_r.to_excel(w, sheet_name=f"Ruolo_{ruolo}", index=False)
        df2.sort_values(f"Squadra Attuale ({args.anno}-{args.anno+1})").to_excel(w, sheet_name="Per_Squadra", index=False)
    print(f"OK {out} — {len(df2)} gioc, {len(df2[df2['Hidden Gem?']=='SÌ'])} gem")

if __name__=="__main__": main()
