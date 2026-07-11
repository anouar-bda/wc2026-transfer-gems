"""
03_name_matching.py

Merges the FBref performance dataset with the Transfermarkt market value
dataset. Player names are rarely written identically across the two sources
(accents, nicknames, suffixes, ordering), so this script performs matching
in progressively looser rounds and only falls back to fuzzy matching for
whatever remains unmatched after the cheap, safe rounds are done.

Rounds:
    1. Exact match on (normalised name, team)
    2. Exact match on normalised name only (handles team-name discrepancies,
       e.g. "USA" vs "United States")
    3. Fuzzy match on normalised name within the same team, using a
       similarity threshold

Output:
    data/processed/merged_players.csv         - matched players
    data/processed/unmatched_fbref.csv         - FBref rows with no match
    data/processed/unmatched_transfermarkt.csv - Transfermarkt rows with no match
"""

import re
import unicodedata
import pandas as pd
from rapidfuzz import fuzz, process

FBREF_PATH = "data/raw/fbref_players_raw.csv"
TRANSFERMARKT_PATH = "data/raw/transfermarkt_players_raw.csv"

OUTPUT_MERGED = "data/processed/merged_players.csv"
OUTPUT_UNMATCHED_FBREF = "data/processed/unmatched_fbref.csv"
OUTPUT_UNMATCHED_TM = "data/processed/unmatched_transfermarkt.csv"

FUZZY_MATCH_THRESHOLD = 87  # 0-100, tuned empirically against manual spot checks


def normalise_name(name: str) -> str:
    """
    Strips accents, lowercases, removes punctuation, and collapses
    whitespace so that e.g. "Rodrygo" vs "Rodrygo Goes" or
    "Şükrü" vs "Sukru" have a fighting chance of matching.
    """
    if not isinstance(name, str):
        return ""

    # Strip accents
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))

    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def round_1_exact_name_and_team(fbref: pd.DataFrame, tm: pd.DataFrame):
    """Exact match on normalised name AND team."""
    merged = fbref.merge(
        tm,
        on=["name_norm", "Team"],
        how="inner",
        suffixes=("_fbref", "_tm"),
    )
    matched_fbref_idx = set(
        fbref.merge(merged[["name_norm", "Team"]].drop_duplicates(),
                    on=["name_norm", "Team"], how="inner").index
    )
    return merged, matched_fbref_idx


def round_2_exact_name_only(fbref_remaining: pd.DataFrame, tm_remaining: pd.DataFrame):
    """Exact match on normalised name only, ignoring team (catches team-label mismatches)."""
    merged = fbref_remaining.merge(
        tm_remaining,
        on="name_norm",
        how="inner",
        suffixes=("_fbref", "_tm"),
    )
    return merged


def round_3_fuzzy_match(fbref_remaining: pd.DataFrame, tm_remaining: pd.DataFrame):
    """
    Fuzzy match remaining FBref players against remaining Transfermarkt
    players, restricted to the same team to keep the search space small
    and reduce false positives.
    """
    matches = []
    used_tm_indices = set()

    for team in fbref_remaining["Team"].unique():
        fbref_team = fbref_remaining[fbref_remaining["Team"] == team]
        tm_team = tm_remaining[tm_remaining["Team"] == team]

        if tm_team.empty:
            continue

        choices = tm_team["name_norm"].tolist()

        for idx, row in fbref_team.iterrows():
            result = process.extractOne(
                row["name_norm"], choices, scorer=fuzz.token_sort_ratio
            )
            if result is None:
                continue

            match_name, score, _ = result
            if score >= FUZZY_MATCH_THRESHOLD:
                tm_row = tm_team[tm_team["name_norm"] == match_name].iloc[0]
                if tm_row.name in used_tm_indices:
                    continue
                used_tm_indices.add(tm_row.name)

                combined_row = {**row.to_dict(), **tm_row.to_dict(), "match_score": score}
                matches.append(combined_row)

    return pd.DataFrame(matches), used_tm_indices


def main():
    fbref = pd.read_csv(FBREF_PATH)
    tm = pd.read_csv(TRANSFERMARKT_PATH)

    fbref["name_norm"] = fbref["Player"].apply(normalise_name)
    tm["name_norm"] = tm["Player"].apply(normalise_name)

    # --- Round 1: exact name + team ---
    round1_merged = fbref.merge(
        tm, on=["name_norm", "Team"], how="inner", suffixes=("_fbref", "_tm")
    )
    matched_keys_r1 = set(zip(round1_merged["name_norm"], round1_merged["Team"]))

    fbref_r2 = fbref[~fbref.apply(lambda r: (r["name_norm"], r["Team"]) in matched_keys_r1, axis=1)]
    tm_r2 = tm[~tm.apply(lambda r: (r["name_norm"], r["Team"]) in matched_keys_r1, axis=1)]

    # --- Round 2: exact name only ---
    round2_merged = fbref_r2.merge(tm_r2, on="name_norm", how="inner", suffixes=("_fbref", "_tm"))
    matched_names_r2 = set(round2_merged["name_norm"])

    fbref_r3 = fbref_r2[~fbref_r2["name_norm"].isin(matched_names_r2)]
    tm_r3 = tm_r2[~tm_r2["name_norm"].isin(matched_names_r2)]

    # --- Round 3: fuzzy match within same team ---
    round3_merged, used_tm_indices = round_3_fuzzy_match(fbref_r3, tm_r3)

    # Combine all rounds
    all_merged = pd.concat([round1_merged, round2_merged, round3_merged], ignore_index=True)

    # Work out what's genuinely still unmatched
    matched_fbref_names = set(all_merged["name_norm"])
    unmatched_fbref = fbref[~fbref["name_norm"].isin(matched_fbref_names)]

    matched_tm_names = set(all_merged["name_norm"]) if "name_norm" in all_merged.columns else set()
    unmatched_tm = tm[~tm["name_norm"].isin(matched_tm_names)]

    all_merged.to_csv(OUTPUT_MERGED, index=False)
    unmatched_fbref.to_csv(OUTPUT_UNMATCHED_FBREF, index=False)
    unmatched_tm.to_csv(OUTPUT_UNMATCHED_TM, index=False)

    total_players = len(fbref)
    merge_rate = len(all_merged) / total_players * 100 if total_players else 0

    print(f"Round 1 (exact name+team):  {len(round1_merged)} matches")
    print(f"Round 2 (exact name only):  {len(round2_merged)} matches")
    print(f"Round 3 (fuzzy, same team): {len(round3_merged)} matches")
    print(f"\nTotal matched: {len(all_merged)} / {total_players} ({merge_rate:.1f}%)")
    print(f"Unmatched FBref players saved to {OUTPUT_UNMATCHED_FBREF} for manual review")


if __name__ == "__main__":
    main()
