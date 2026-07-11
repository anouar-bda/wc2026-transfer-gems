"""
01_scrape_fbref.py

Collects player performance statistics from FBref for all 48 teams
participating in the 2026 World Cup.

FBref publishes standard stats tables (per-90 stats, shooting, passing,
defensive actions, etc.) on each team/competition page as standard HTML
tables, which pandas.read_html can parse directly.

Output: data/raw/fbref_players_raw.csv
"""

import time
import random
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Map of team name -> FBref squad URL.
# Fill this in with the 48 qualified squads' FBref URLs.
# Example format shown below for a couple of teams.
TEAM_URLS = {
    "England": "https://fbref.com/en/squads/1c781004/England-Stats",
    "France": "https://fbref.com/en/squads/e2d8892c/France-Stats",
    # ... add remaining teams (48 total)
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

OUTPUT_PATH = "data/raw/fbref_players_raw.csv"

# FBref rate-limits aggressively; stay well under their request threshold.
MIN_DELAY_SECONDS = 4
MAX_DELAY_SECONDS = 7


def fetch_team_standard_stats(team_name: str, url: str) -> pd.DataFrame:
    """
    Fetches the 'Standard Stats' table for a single team from FBref
    and returns it as a tidy DataFrame with a Team column attached.
    """
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    # FBref standard stats tables are HTML comments on the page in some
    # sections; pandas.read_html on the raw response text handles the
    # visible tables. The "Standard Stats" table is typically the first
    # matching table with a multi-index header.
    tables = pd.read_html(response.text)

    standard_stats = None
    for table in tables:
        # Standard Stats tables have MultiIndex columns (e.g. "Playing Time", "Gls")
        if isinstance(table.columns, pd.MultiIndex):
            standard_stats = table
            break

    if standard_stats is None:
        raise ValueError(f"Could not locate standard stats table for {team_name}")

    # Flatten MultiIndex columns: ('Playing Time', 'MP') -> 'Playing Time_MP'
    standard_stats.columns = [
        "_".join([str(c) for c in col if "Unnamed" not in str(c)]).strip("_")
        for col in standard_stats.columns
    ]

    # Drop repeated header rows that FBref inserts periodically in long tables
    if "Player" in standard_stats.columns:
        standard_stats = standard_stats[standard_stats["Player"] != "Player"]

    standard_stats["Team"] = team_name
    return standard_stats


def main():
    all_rows = []

    for i, (team_name, url) in enumerate(TEAM_URLS.items(), start=1):
        print(f"[{i}/{len(TEAM_URLS)}] Fetching {team_name}...")
        try:
            team_df = fetch_team_standard_stats(team_name, url)
            all_rows.append(team_df)
        except Exception as exc:
            print(f"  Failed to fetch {team_name}: {exc}")

        # Be a polite scraper - randomised delay to avoid hammering FBref
        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    if not all_rows:
        raise RuntimeError("No data collected - check TEAM_URLS and network access.")

    combined = pd.concat(all_rows, ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(combined)} player rows across {len(all_rows)} teams to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
