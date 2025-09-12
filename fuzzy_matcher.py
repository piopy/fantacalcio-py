import pandas as pd
import json
import re
from typing import Dict, List, Tuple, Optional
from fuzzywuzzy import fuzz, process
from unidecode import unidecode


def normalize_name(name: str) -> str:
    if pd.isna(name):
        return ""
    name = unidecode(str(name)).lower()
    name = re.sub(r"['\-\.]", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_team_name(team: str) -> str:
    if pd.isna(team):
        return ""
    if isinstance(team, str) and team.startswith("{"):
        import ast

        try:
            team_dict = ast.literal_eval(team)
            team = team_dict.get("name", team)
        except:
            pass
    return unidecode(str(team)).lower().strip()


def find_best_match(
    target_name: str,
    target_team: str,
    candidates: List[Tuple[str, str, str]],
    min_similarity: float = 60.0,
) -> Optional[Tuple[str, float]]:
    if not candidates:
        return None

    candidate_names = [candidate[0] for candidate in candidates]
    candidate_originals = [candidate[2] for candidate in candidates]
    candidate_teams = [candidate[1] for candidate in candidates]

    best_match = process.extractOne(
        target_name,
        candidate_names,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=min_similarity,
    )

    if best_match:
        matched_name, score = best_match
        match_idx = candidate_names.index(matched_name)
        original_name = candidate_originals[match_idx]
        matched_team = candidate_teams[match_idx]

        if target_team == matched_team:
            score += 10

        return (original_name, score)
    return None


def load_and_preprocess_data(
    giocatori_file: str, players_file: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df_giocatori = pd.read_csv(giocatori_file)
    df_players = pd.read_csv(players_file, sep=";")

    df_giocatori["nome_normalized"] = df_giocatori["Nome"].apply(normalize_name)
    df_giocatori["squadra_normalized"] = df_giocatori["Squadra"].apply(
        normalize_team_name
    )

    df_players["full_name"] = (
        df_players["firstname"].fillna("") + " " + df_players["lastname"].fillna("")
    ).str.strip()
    df_players["nome_normalized"] = df_players["full_name"].apply(normalize_name)
    df_players["squadra_normalized"] = df_players["team"].apply(normalize_team_name)

    return df_giocatori, df_players


def create_fuzzy_mapping(
    giocatori_file: str = "data/_giocatori.csv",
    players_file: str = "data/_players.csv",
    min_similarity: float = 60.0,
    use_team_filter: bool = True,
) -> Tuple[Dict[str, str], List[str], List[str]]:
    df_giocatori, df_players = load_and_preprocess_data(giocatori_file, players_file)
    mapping = {}
    unmapped_giocatori = []
    mapped_players = set()

    if use_team_filter:
        teams_giocatori = df_giocatori["squadra_normalized"].unique()

        for team in teams_giocatori:
            if not team:
                continue

            team_giocatori = df_giocatori[df_giocatori["squadra_normalized"] == team]
            team_players = df_players[df_players["squadra_normalized"] == team]

            if len(team_players) == 0:
                team_players = df_players

            candidates = [
                (
                    row_cand["nome_normalized"],
                    row_cand["squadra_normalized"],
                    row_cand["full_name"],
                )
                for _, row_cand in team_players.iterrows()
                if row_cand["nome_normalized"]
            ]

            for _, row in team_giocatori.iterrows():
                target_name = row["nome_normalized"]
                target_team = row["squadra_normalized"]
                original_name_giocatori = row["Nome"]

                if not target_name:
                    continue

                best_match = find_best_match(
                    target_name, target_team, candidates, min_similarity
                )

                if best_match:
                    match_name, similarity = best_match
                    mapping[original_name_giocatori] = match_name
                    mapped_players.add(match_name)
                    candidates = [c for c in candidates if c[2] != match_name]
                else:
                    unmapped_giocatori.append(original_name_giocatori)
    else:
        for idx, row in df_giocatori.iterrows():
            target_name = row["nome_normalized"]
            target_team = row["squadra_normalized"]
            original_name_giocatori = row["Nome"]

            if not target_name:
                continue

            candidates = [
                (
                    row_cand["nome_normalized"],
                    row_cand["squadra_normalized"],
                    row_cand["full_name"],
                )
                for _, row_cand in df_players.iterrows()
                if row_cand["nome_normalized"]
            ]

            best_match = find_best_match(
                target_name, target_team, candidates, min_similarity
            )

            if best_match:
                match_name, similarity = best_match
                mapping[original_name_giocatori] = match_name
                mapped_players.add(match_name)
            else:
                unmapped_giocatori.append(original_name_giocatori)

    # Trova giocatori non mappati dal secondo dataset
    unmapped_players = [
        row["full_name"]
        for _, row in df_players.iterrows()
        if row["full_name"] and row["full_name"] not in mapped_players
    ]

    return mapping, unmapped_giocatori, unmapped_players


def find_partial_matches(
    unmapped_1: List[str],
    unmapped_2: List[str],
    df_giocatori: pd.DataFrame,
    df_players: pd.DataFrame,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Trova match parziali tra giocatori non mappati usando split dei nomi e controllo squadre.
    Restituisce due dizionari: (nome+squadra, solo_nome)
    """
    probably_mapped_ns = {}  # nome + squadra
    probably_mapped_n = {}  # solo nome
    used_players = set()

    # Crea mapping nome -> squadra per entrambi i dataset
    giocatori_teams = dict(
        zip(df_giocatori["Nome"], df_giocatori["squadra_normalized"])
    )
    players_teams = dict(zip(df_players["full_name"], df_players["squadra_normalized"]))

    for unmapped_g in unmapped_1:
        if not unmapped_g:
            continue

        # Split del nome in parti
        name_parts_g = normalize_name(unmapped_g).split()
        team_g = giocatori_teams.get(unmapped_g, "")

        for unmapped_p in unmapped_2:
            if not unmapped_p or unmapped_p in used_players:
                continue

            name_parts_p = normalize_name(unmapped_p).split()
            team_p = players_teams.get(unmapped_p, "")

            # Controlla se c'è almeno una parte del nome in comune
            common_parts = set(name_parts_g) & set(name_parts_p)

            if common_parts:
                # Se hanno anche la stessa squadra, è un match molto probabile
                if team_g == team_p and team_g:
                    probably_mapped_ns[unmapped_g] = unmapped_p
                    used_players.add(unmapped_p)
                    break
                # Se hanno parti in comune significative (non nomi troppo corti)
                elif any(len(part) >= 4 for part in common_parts):
                    probably_mapped_n[unmapped_g] = unmapped_p
                    used_players.add(unmapped_p)
                    break

    return probably_mapped_ns, probably_mapped_n


def get_team_info_for_unmapped(
    unmapped_list: List[str], df: pd.DataFrame, name_col: str
) -> Dict[str, str]:
    """
    Restituisce informazioni sulle squadre per i giocatori non mappati.
    """
    team_info = {}
    name_to_team = dict(zip(df[name_col], df["squadra_normalized"]))

    for player in unmapped_list:
        team = name_to_team.get(player, "Unknown")
        team_info[player] = team

    return team_info


def save_mapping_to_json(
    mapping: Dict[str, str],
    unmapped_1: List[str],
    unmapped_2: List[str],
    probably_mapped_ns: Dict[str, str] = None,
    probably_mapped_n: Dict[str, str] = None,
    output_file: str = "player_mapping.json",
):
    data = {
        "mapping": mapping,
        "unmapped_1": sorted(unmapped_1),
        "unmapped_2": sorted(unmapped_2),
        "stats": {
            "mapped_count": len(mapping),
            "unmapped_1_count": len(unmapped_1),
            "unmapped_2_count": len(unmapped_2),
        },
    }

    if probably_mapped_ns:
        data["probably_mapped_ns"] = probably_mapped_ns
        data["stats"]["probably_mapped_ns_count"] = len(probably_mapped_ns)

    if probably_mapped_n:
        data["probably_mapped_n"] = probably_mapped_n
        data["stats"]["probably_mapped_n_count"] = len(probably_mapped_n)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    mapping, unmapped_1, unmapped_2 = create_fuzzy_mapping(
        min_similarity=60.0, use_team_filter=True
    )

    # Carica i dati per il partial matching
    df_giocatori, df_players = load_and_preprocess_data(
        "data/_giocatori.csv", "data/_players.csv"
    )

    # Trova match parziali (separati per confidenza)
    probably_mapped_ns, probably_mapped_n = find_partial_matches(
        unmapped_1, unmapped_2, df_giocatori, df_players
    )

    # Dopo aver visto i primi risultati non mi affiderei a questo dizionario manco morto
    probably_mapped_n = {}

    # Combina tutti i probably mapped per rimuoverli dai non mappati
    all_probably_mapped = {**probably_mapped_ns, **probably_mapped_n}

    # Rimuovi dai non mappati quelli che sono stati probabilmente mappati
    final_unmapped_1 = [p for p in unmapped_1 if p not in all_probably_mapped]
    final_unmapped_2 = [p for p in unmapped_2 if p not in all_probably_mapped.values()]

    save_mapping_to_json(
        mapping,
        final_unmapped_1,
        final_unmapped_2,
        probably_mapped_ns,
        probably_mapped_n,
    )

    print(f"Mapped {len(mapping)} players")
    print(f"Probably mapped with team info: {len(probably_mapped_ns)} players")
    print(f"Probably mapped name-only: {len(probably_mapped_n)} players")
    print(f"Total probably mapped: {len(all_probably_mapped)} players")
    print(f"Still unmapped from dataset 1: {len(final_unmapped_1)}")
    print(f"Still unmapped from dataset 2: {len(final_unmapped_2)}")

    return mapping, final_unmapped_1, final_unmapped_2, all_probably_mapped


if __name__ == "__main__":
    main()
