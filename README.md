📌 Project Overview

Every scout knows Mbappé, Haaland, and Bellingham. This project finds the players they don't — the ones performing at World Cup level whose market value hasn't caught up to their ability.
Using data from FBref (performance statistics) and Transfermarkt (market values), I built a position-specific scoring model that ranks players by Transfer Opportunity Score — balancing what they do on the pitch with what they cost.
Output: Top 5 transfer opportunities per position (FW, MF, DF, GK) with a recommended shortlist for further scouting.
---
🔍 Business Question
> \\\*"Which World Cup 2026 players offer the highest transfer value based on their tournament performances?"\\\*
Supporting Questions
Which forward is the best transfer target?
Which midfielder is the best transfer target?
Which defender is the best transfer target?
Which goalkeeper is the best transfer target?
---
📊 Data Sources
Source	What It Provides	Players
FBref.com	Goals, assists, shots, tackles, interceptions, saves, clean sheets, cards, minutes	1,247
Transfermarkt.com	Market value (€M), age, position, height, foot	1,248
Data collected: July 2026
Coverage: All 48 World Cup 2026 squads (Group Stage + Round of 32)
Minimum threshold: 135 minutes played (half the group stage)
Final merged dataset: 1,161 players matched across both sources (99.8% match rate)
---
🛠️ Methodology
Step 1 — Data Collection
Extracted player statistics from FBref by saving all 48 team pages as HTML files
Python (`pandas.read\\\_html`) parsed 5 statistical tables per team:
Roster (name, position, club, age)
Standard Stats (goals, assists, minutes, cards)
Shooting (shots, shots on target, conversion rates)
Goalkeeping (saves, save %, clean sheets, goals against)
Miscellaneous (tackles won, interceptions, fouls, crosses)
Transfermarkt data collected separately: market value, age, height, foot, position
Kaggle dataset evaluated and rejected due to incorrect player names and fabricated data
Step 2 — Data Cleaning (Python)
Fixed multi-level headers from FBref HTML tables
Standardised country names across sources (e.g., "Korea Repulic" → "Korea Republic", "United  States" → "United States")
Removed duplicate rows, summary rows ("Squad Total", "Opponent Total"), and blank entries
Converted text columns to numeric types
Assigned primary position for dual-position players ("FW,MF" → "FW")
Step 3 — Data Merging
Created normalised name keys: lowercase, accents removed, hyphens stripped
Merged FBref + Transfermarkt on `match\\\_name` + `Country`
Resolved 213 name mismatches through automated normalisation and 7 rounds of manual corrections
Korean player names required reversal (family name first vs given name first)
Final match rate: 99.8% (only 2 players unmatched — no Transfermarkt profiles)
Step 4 — Scoring Model
Weights:
Component	Weight	Rationale
Position-Specific Performance	40% (4 metrics × 10%)	The player has to be good
Market Value (inverse)	35%	This is about opportunities, not just talent
Age (inverse — younger = better)	25%	Younger players have more upside and resale value
Position-Specific Performance Metrics:
Position	Metric 1	Metric 2	Metric 3	Metric 4
FW	Goals/90	Assists/90	Conversion Rate (G/SoT)	Fouls Drawn
MF	Assists/90	Tackles Won	Interceptions	Fouls Committed (inverse)
DF	Tackles Won	Interceptions	Goals/90	Fouls Committed (inverse)
GK	Save %	Goals Against/90 (inverse)	Clean Sheets	Total Saves
Normalisation: Min-max scaling (0-100) applied within each position group. Inverse normalisation used for metrics where lower is better (market value, age, fouls, goals against).
Transfer Opportunity Score = (Performance × 0.40) + (Value × 0.35) + (Age × 0.25)
---
📈 Key Findings
Top 5 Forwards
Rank	Player	Country	Age	Value (€M)	Score
1	Julio Enciso	Paraguay	22	25.0	74.6
2	Crysencio Summerville	Netherlands	24	35.0	71.5
3	Deniz Undav	Germany	29	22.0	70.8
4	Nestory Irankunda	Australia	20	8.0	67.7
5	Brian Brobbey	Netherlands	24	30.0	67.1
Top 5 Midfielders
Rank	Player	Country	Age	Value (€M)	Score
1	Pedro Vite	Ecuador	24	6.0	74.9
2	Nathan Saliba	Canada	22	7.5	72.7
3	Paul Okon-Engstler	Australia	21	1.2	72.4
4	Livano Comenencia	Curaçao	22	0.5	72.3
5	Alexandr Sojka	Czechia	23	2.3	70.0
Top 5 Defenders
Rank	Player	Country	Age	Value (€M)	Score
1	Alex Freeman	United States	21	3.5	75.6
2	Omar Rekik	Tunisia	24	0.5	74.1
3	Mbekezeli Mbokazi	South Africa	20	3.5	70.5
4	Sidny Lopes Cabral	Cape Verde	23	4.0	70.1
5	Ime Okon	South Africa	22	2.0	69.3
Top 5 Goalkeepers
Rank	Player	Country	Age	Value (€M)	Score
1	Patrick Beach	Australia	22	1.0	86.7
2	Raúl Rangel	Mexico	26	6.5	80.6
3	Orlando Gill	Paraguay	26	6.0	78.4
4	Matt Freese	United States	27	2.0	74.4
5	Yahia Fofana	Ivory Coast	25	5.0	73.5
---
💡 Key Insight
This is not a list of the tournament's best players. It's a data-informed scouting shortlist identifying players who:
Performed above their market value at the World Cup
Are young enough to offer development upside and resale value
Could be available at a reasonable transfer fee
The final recruitment decision depends on factors this data cannot capture — tactical fit, personality, injury history, and club ambitions. What the data does is point scouts in the right direction and ensure promising players from less visible markets don't get overlooked.
---
⚠️ Limitations
Small sample size: 3-4 matches per player. Tournament form doesn't always reflect long-term ability.
Team effects: Individual stats are influenced by team tactics, formation, and opposition quality.
Market values are estimates: Transfermarkt values are crowd-sourced proxies, not actual transfer fees.
Missing advanced metrics: xG, progressive carries, and pressing data require paid platforms (StatsBomb, Wyscout) not available for this project.
Performance weights require justification: The 10% equal weighting across performance metrics is a simplification. A production model would optimise weights based on historical transfer success data.
---
🧰 Tools & Technologies
Tool	Purpose
Python (pandas)	Data collection, cleaning, merging, scoring model
SQL	Data querying and analysis
Power BI	Interactive dashboard and visualisation
FBref.com	Player performance data source
Transfermarkt.com	Market value and player profile data source
---
📁 Repository Structure
```
wc2026-transfer-gems/
├── data/
│   ├── transfermarkt\\\_all.csv
│   ├── merged\\\_dataset.csv
│   ├── ranked\\\_forwards.csv
│   ├── ranked\\\_midfielders.csv
│   ├── ranked\\\_defenders.csv
│   └── ranked\\\_goalkeepers.csv
├── scripts/
│   ├── extract\\\_data.py
│   ├── clean\\\_and\\\_merge.py
│   └── scoring\\\_model.py
├── dashboard/
│   └── WC2026\\\_Hidden\\\_Gems.pbix
└── README.md
```
---
🚀 How to Reproduce
Clone this repository
Place FBref HTML pages in `perfwc26/` folder and Transfermarkt pages in `tmwc26/` folder
Run scripts in order:
```
   python scripts/extract\\\_data.py
   python scripts/clean\\\_and\\\_merge.py
   python scripts/scoring\\\_model.py
   ```
Open `dashboard/WC2026\\\_Hidden\\\_Gems.pbix` in Power BI Desktop
---
📬 Contact
Anouar Lacheheb
MSc International Business with Data Analytics | Manchester, UK
https://www.linkedin.com/in/anouar-lacheheb-328052398/
anouar.aus@gmail.com

Built for football. Driven by data.
