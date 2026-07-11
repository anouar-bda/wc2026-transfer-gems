"""
02_scrape_transfermarkt.py

Collects player market value data from Transfermarkt for all 48 teams
participating in the 2026 World Cup.

Transfermarkt squad pages list each player's age, position, and current
market value in a standard HTML table.

Output: data/raw/transfermarkt_players_raw.csv
"""

import time
import random
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Map of team name -> Transfermarkt squad URL.
# Fill this in with the 48 qualified squads' Transfermarkt URLs.
TEAM_URLS = {
    "England": "https://www.transfermarkt.com/england/startseite/verein/3299",
    "France": "https://www.transfermarkt.com/frankreich/startseite/verein/3546",
    # ... add remaining teams (48 total)
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

OUTPUT_PATH = "data/raw/transfermarkt_players_raw.csv"

MIN_DELAY_SECONDS = 4
MAX_DELAY_SECONDS = 7


def parse_market_value(value_str: str) -> float:
    """
    Converts Transfermarkt's market value strings (e.g. '€45.00m', '€800k')
    into a numeric value in euros.
    """
    if not value_str:
        return None

    value_str = value_str.replace("€", "").strip()
    multiplier = 1

    if value_str.endswith("m"):
        multiplier = 1_000_000
        value_str = value_str[:-1]
    elif value_str.endswith("k"):
        multiplier = 1_000
        value_str = value_str[:-1]

    try:
        return float(value_str) * multiplier
    except ValueError:
        return None


def fetch_team_market_values(team_name: str, url: str) -> pd.DataFrame:
    """
    Fetches player name, position, age, and market value for a single
    team's squad page.
    """
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="items")

    if table is None:
        raise ValueError(f"Could not locate squad table for {team_name}")

    rows = table.find("tbody").find_all("tr", recursive=False)

    records = []
    for row in rows:
        name_cell = row.find("td", class_="posrela")
        if name_cell is None:
            continue

        name_tag = name_cell.find("a")
        player_name = name_tag.text.strip() if name_tag else None

        position_tag = name_cell.find("td", class_="inline-table").find_all("tr")
        position = position_tag[1].text.strip() if len(position_tag) > 1 else None

        age_cell = row.find_all("td", class_="zentriert")
        age = None
        for cell in age_cell:
            match = re.search(r"\((\d{2})\)", cell.text)
            if match:
                age = int(match.group(1))
                break

        value_cell = row.find("td", class_="rechts")
        market_value = parse_market_value(value_cell.text.strip()) if value_cell else None

        if player_name:
            records.append({
                "Player": player_name,
                "Position_TM": position,
                "Age_TM": age,
                "MarketValue_EUR": market_value,
                "Team": team_name,
            })

    return pd.DataFrame(records)


def main():
    all_rows = []

    for i, (team_name, url) in enumerate(TEAM_URLS.items(), start=1):
        print(f"[{i}/{len(TEAM_URLS)}] Fetching {team_name}...")
        try:
            team_df = fetch_team_market_values(team_name, url)
            all_rows.append(team_df)
        except Exception as exc:
            print(f"  Failed to fetch {team_name}: {exc}")

        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    if not all_rows:
        raise RuntimeError("No data collected - check TEAM_URLS and network access.")

    combined = pd.concat(all_rows, ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(combined)} player rows across {len(all_rows)} teams to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
