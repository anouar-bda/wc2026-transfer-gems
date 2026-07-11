"""
04_scoring_model.py

Builds the "Hidden Gem" score for each player using a position-specific
weighted model:

    Hidden Gem Score = 0.40 * Performance Score
                      + 0.35 * Value Score
                      + 0.25 * Age Score

Design notes
------------
- Performance metrics are position-specific: a striker is judged on goals
  and shot quality, a centre-back on defensive actions and aerial duels,
  etc. Each position group uses its own set of per-90 metrics.
- Within the performance score, per-90 metrics are squared after
  normalisation (rather than combined linearly) so that standout, elite-
  level output pulls a player's score up disproportionately relative to
  merely "solid" output. A player putting up 2x the goals per 90 of a
  teammate should not just get 2x the points - they should stand out more
  sharply, which is what squaring after normalisation achieves.
- The Value Score deliberately does NOT compare a player's output to their
  transfer fee or "price the market would pay", because in this dataset
  market value reflects club-level transfer market dynamics -- and
  national teams do not buy or sell players. Instead, Value Score captures
  underratedness: how much a player is achieving relative to their current
  market value, i.e. the gap between performance rank and value rank
  within their position group. This is what actually identifies a "hidden
  gem" for a scouting/analytics audience, rather than assuming any
  transfer-market transaction is happening at the international level.
- Age Score rewards younger players (more resale/development value) using
  a smooth curve rather than hard age cutoffs.

Output: data/processed/wc2026_hidden_gems_scored.csv
"""

import numpy as np
import pandas as pd

INPUT_PATH = "data/processed/merged_players.csv"
OUTPUT_PATH = "data/processed/wc2026_hidden_gems_scored.csv"

PERFORMANCE_WEIGHT = 0.40
VALUE_WEIGHT = 0.35
AGE_WEIGHT = 0.25

# Position-specific per-90 metrics used to build the Performance Score.
# Column names assume the FBref standard/shooting/passing/defense tables
# have been merged and flattened upstream - adjust to match your actual
# merged column names.
POSITION_METRIC_GROUPS = {
    "Forward": ["Gls_per90", "xG_per90", "SCA_per90", "Sh_per90"],
    "Midfielder": ["xA_per90", "PrgP_per90", "SCA_per90", "Tkl_per90"],
    "Defender": ["Tkl_per90", "Int_per90", "Clr_per90", "AerialWon_pct"],
    "Goalkeeper": ["Saves_pct", "PSxG_minus_GA_per90", "Cmp_pct_long"],
}


def min_max_normalise(series: pd.Series) -> pd.Series:
    """Scales a series to the 0-1 range. Constant columns return 0.5 for all rows."""
    min_val, max_val = series.min(), series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val)


def map_to_position_group(position_str: str) -> str:
    """Buckets detailed position strings (e.g. 'RB', 'CB', 'DM') into the
    four broad groups used for scoring."""
    if not isinstance(position_str, str):
        return "Midfielder"  # safest default if position is missing

    position_str = position_str.upper()

    if "GK" in position_str or "GOALKEEPER" in position_str:
        return "Goalkeeper"
    if any(tag in position_str for tag in ["CB", "RB", "LB", "WB", "DEFENDER"]):
        return "Defender"
    if any(tag in position_str for tag in ["CF", "ST", "FW", "WING", "FORWARD"]):
        return "Forward"
    return "Midfielder"


def compute_performance_score(df: pd.DataFrame) -> pd.Series:
    """
    Computes a 0-1 Performance Score per player, using position-specific
    metrics, normalised then squared to reward standout output.
    """
    scores = pd.Series(index=df.index, dtype=float)

    for position_group, metrics in POSITION_METRIC_GROUPS.items():
        group_mask = df["PositionGroup"] == position_group
        group_df = df.loc[group_mask]

        if group_df.empty:
            continue

        available_metrics = [m for m in metrics if m in df.columns]
        if not available_metrics:
            raise KeyError(
                f"None of the expected metrics {metrics} for {position_group} "
                f"were found in the merged dataset. Check column names from "
                f"the FBref merge step."
            )

        normalised_components = []
        for metric in available_metrics:
            normalised = min_max_normalise(group_df[metric].fillna(0))
            squared = normalised ** 2  # reward elite outliers over "solid" output
            normalised_components.append(squared)

        component_matrix = pd.concat(normalised_components, axis=1)
        group_score = component_matrix.mean(axis=1)

        # Re-normalise the squared, averaged score back to 0-1 within the group
        scores.loc[group_mask] = min_max_normalise(group_score)

    return scores.fillna(0)


def compute_value_score(df: pd.DataFrame) -> pd.Series:
    """
    Computes a 0-1 Value Score representing "underratedness": players whose
    performance rank is much higher than their market-value rank within
    their position group score highly here. This deliberately avoids
    treating market value as a price a national team would pay, since
    international squads are not transfer-market participants.
    """
    scores = pd.Series(index=df.index, dtype=float)

    for position_group in POSITION_METRIC_GROUPS.keys():
        group_mask = df["PositionGroup"] == position_group
        group_df = df.loc[group_mask]

        if group_df.empty:
            continue

        performance_rank = group_df["PerformanceScore"].rank(pct=True)
        # Lower market value = higher "cheapness" rank
        value_rank = (1 - min_max_normalise(group_df["MarketValue_EUR"].fillna(
            group_df["MarketValue_EUR"].median()
        )))

        # A hidden gem performs well AND is undervalued relative to peers.
        underratedness = performance_rank - (1 - value_rank)
        scores.loc[group_mask] = min_max_normalise(underratedness)

    return scores.fillna(0)


def compute_age_score(df: pd.DataFrame) -> pd.Series:
    """
    Rewards younger players using a smooth decreasing curve rather than a
    hard cutoff, peaking for players in their early-to-mid twenties and
    tapering off gradually for older players.
    """
    age = df["Age_TM"].fillna(df["Age_TM"].median())
    peak_age = 24
    # Gaussian-style decay centred on peak_age
    age_score = np.exp(-((age - peak_age) ** 2) / (2 * 6 ** 2))
    return min_max_normalise(age_score)


def main():
    df = pd.read_csv(INPUT_PATH)

    df["PositionGroup"] = df["Position_TM"].apply(map_to_position_group)

    df["PerformanceScore"] = compute_performance_score(df)
    df["ValueScore"] = compute_value_score(df)
    df["AgeScore"] = compute_age_score(df)

    df["HiddenGemScore"] = (
        PERFORMANCE_WEIGHT * df["PerformanceScore"]
        + VALUE_WEIGHT * df["ValueScore"]
        + AGE_WEIGHT * df["AgeScore"]
    )

    # Rank within position group so the dashboard can slice by position
    df["RankInPosition"] = (
        df.groupby("PositionGroup")["HiddenGemScore"].rank(ascending=False, method="min")
    )

    df = df.sort_values("HiddenGemScore", ascending=False)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Scored {len(df)} players.")
    print("\nTop 10 hidden gems overall:")
    print(
        df[["Player", "Team", "PositionGroup", "HiddenGemScore"]]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
