"""
05_export_for_powerbi.py

Takes the scored player dataset and prepares a clean, presentation-ready
export for the Power BI dashboard: trims to the columns actually used by
the report visuals, renames them to friendly labels, and rounds numeric
fields for cleaner display in gauges/tables.

Output: data/processed/wc2026_dashboard_export.csv
"""

import pandas as pd

INPUT_PATH = "data/processed/wc2026_hidden_gems_scored.csv"
OUTPUT_PATH = "data/processed/wc2026_dashboard_export.csv"

# Columns to keep and their friendly display names for Power BI
COLUMN_MAP = {
    "Player": "Player",
    "Team": "Team",
    "PositionGroup": "Position",
    "Age_TM": "Age",
    "MarketValue_EUR": "Market Value (EUR)",
    "PerformanceScore": "Performance Score",
    "ValueScore": "Value Score",
    "AgeScore": "Age Score",
    "HiddenGemScore": "Hidden Gem Score",
    "RankInPosition": "Rank In Position",
}

ROUND_DECIMALS = {
    "Performance Score": 3,
    "Value Score": 3,
    "Age Score": 3,
    "Hidden Gem Score": 3,
    "Market Value (EUR)": 0,
}


def main():
    df = pd.read_csv(INPUT_PATH)

    missing_cols = [c for c in COLUMN_MAP if c not in df.columns]
    if missing_cols:
        raise KeyError(f"Expected columns missing from scored dataset: {missing_cols}")

    export_df = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)

    for col, decimals in ROUND_DECIMALS.items():
        export_df[col] = export_df[col].round(decimals)

    export_df = export_df.sort_values("Hidden Gem Score", ascending=False)
    export_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Exported {len(export_df)} rows to {OUTPUT_PATH}")
    print(f"Columns: {list(export_df.columns)}")


if __name__ == "__main__":
    main()
