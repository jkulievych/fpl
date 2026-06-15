# FPL Hype Tracker

![Demo](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOXIyYjY5aDViZWM1dTR4cjZ1ZHZiZnYxbjZ0N2FnOHhxdzBza3pnbiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/lU21XVNwliGM2gyGaN/giphy.gif)

A web-based analytics dashboard for Fantasy Premier League, built with Python and Flask.
Connects to the official FPL API, applies statistical models, and presents insights through interactive visualisations.

**Course:** Programming in Python 2 — Social Data Science

---

## Features

**Dashboard**
- Player table with Z-score, ROI, form, and price
- Position filter (GK / DEF / MID / FWD)
- Budget slider filtering by max price
- Interactive bubble chart (price vs transfers, coloured by ROI)
- Sentiment-analysed news headlines
- Captain Picks — top 3 midfielders/forwards ranked by a combined form + fixture-ease score

**Player Page**
- Hero card with photo, team badge, and fixture difficulty
- AI verdict card (rule-based recommendation)
- Radar chart vs league averages
- Gameweek-by-gameweek points history chart
- Stats grid and price change prediction bar, with a 95% confidence interval

**Team Optimiser**
- Builds the mathematically optimal 15-player squad using linear programming (PuLP)
- Optimise for total points, form, or ROI within a budget
- Enforces FPL squad rules: 2 GK / 5 DEF / 5 MID / 3 FWD, max 3 players per team

**Usage Stats**
- `/stats` page showing total requests, most-visited pages, and most-searched players
- Backed by a `UsageLog` table populated automatically via a Flask `after_request` hook

---

## How to Run

```bash
pip install flask flask-sqlalchemy pandas plotly textblob requests beautifulsoup4 numpy pulp
python -m textblob.download_corpora   # one time only — TextBlob sentiment corpora
python scrape_photos.py               # one time only — downloads player photos
python app.py
```

Open `http://127.0.0.1:5000` in your browser (or `5001` if port 5000 is taken — see Known Issues below). The database populates automatically on first load.

---

## Project Structure

```
python2project2/
├── app.py                  # Flask routes and application logic
├── database.db             # SQLite database (auto-generated, gitignored)
├── scrape_photos.py        # One-time player photo downloader
├── conftest.py              # Empty file — marks project root for pytest
├── fpl_engine/
│   ├── models.py           # SQLAlchemy models: Player, PlayerSnapshot, UsageLog
│   ├── api_client.py       # FPL API integration + caching + snapshot writing
│   ├── analytics.py        # Z-score, ROI, FDR, price prediction, CI, captain score
│   └── scraper.py          # News scraper + sentiment analysis
├── static/
│   └── player_photos/      # Locally cached player images (gitignored)
├── tests/
│   └── test_analytics.py   # Unit tests for analytics.py
└── templates/
    ├── index.html          # Main dashboard
    ├── player.html          # Player detail page
    ├── optimiser.html       # Team optimiser page
    └── stats.html           # Usage stats page
```

---

## Data Source

All live data comes from the official FPL REST API (no authentication required).

**Main endpoint:**
```
GET https://fantasy.premierleague.com/api/bootstrap-static/
```
Returns all player data: name, price, transfers, points, goals, assists, position, form.

**Fixtures endpoint:**
```
GET https://fantasy.premierleague.com/api/fixtures/
```
Returns all season fixtures with difficulty ratings (1–5) used for the FDR and Captain Picks analysis.

**Gameweek history endpoint:**
```
GET https://fantasy.premierleague.com/api/element-summary/{player_id}/
```
Returns a player's points, goals, assists, and minutes per gameweek, used for the history chart on the player page.

**Caching:** The bootstrap API is only called if the database data is older than one hour, checked via the `last_updated` timestamp on the `Player` model. Each refresh also writes a row per player to `PlayerSnapshot`, building up a historical record over time.

---

## Analytical Methodology

### Z-Score (Market Hype Index)

Measures how many standard deviations a player's transfer activity is above or below the league average. Calculated across all ~840 players each session.

```
Z = (transfers_in - mean) / standard_deviation
```

- Z > 3.0 — extreme anomaly, viral hype
- Z 1–3 — above average interest
- Z < 0 — player being ignored or sold

If every player has identical transfer activity (zero variance — see Known Issues), Z-score is defined as 0 for all players rather than being undefined.

### ROI (Efficiency Index)

Points scored per million pounds spent. Identifies undervalued players who score heavily relative to their cost.

```
ROI = total_points / now_cost
```

### Fixture Difficulty Rating (FDR)

Average difficulty of a team's next 5 fixtures, using FPL's own 1–5 difficulty ratings.

```
FDR_avg = sum(next 5 fixture difficulties) / 5
```

- FDR <= 2.0 — easy run
- FDR 2.0–3.0 — moderate
- FDR > 3.0 — tough

### Price Change Prediction

FPL prices change when net transfer activity exceeds roughly 1% of all managers (~80,000 net transfers). The app estimates pressure toward a price rise or fall:

```
pressure (%) = (|net_transfers| / 80,000) x 100
```

Since transfers_out isn't exposed directly by the API, the app estimates it as 30% of transfers_in as a conservative proxy.

### Price Pressure Confidence Interval

The 30% transfers_out proxy is uncertain, so the app treats it as a random variable rather than a fixed value. A Monte Carlo simulation samples the transfers_out ratio from a Normal distribution (mean 0.30, sd 0.08, clipped to [0.05, 0.60]), recomputes the pressure for each sample, and reports the 2.5th and 97.5th percentiles as a 95% confidence interval alongside the point estimate.

This means the price pressure bar shows both a single best-guess value and a shaded band representing the plausible range given uncertainty in the transfers_out estimate.

### Captain Score

Combines a player's recent form with how easy their upcoming fixtures are, to suggest captaincy picks among midfielders and forwards:

```
captain_score = form * (6 - FDR_avg) / 5
```

Easy fixtures (FDR close to 1) amplify the form score (multiplier close to 1.0); tough fixtures (FDR close to 5) dampen it (multiplier close to 0.2). The top 3 scorers are shown as "Captain Picks" on the dashboard.

### Sentiment Analysis

News headlines are analysed using TextBlob, which returns a polarity score from -1.0 (negative) to +1.0 (positive). Articles are matched to players by surname and displayed on the player detail page.

---

## AI Verdict System

A rule-based system that combines Z-score, ROI, and FDR to produce a recommendation. Conditions are evaluated in priority order.

| Verdict | Condition |
|---|---|
| 🔥 Hot Pick | Z > 3.0 and FDR <= 2.5 |
| ⚠️ Risky Hype | Z > 3.0 and FDR > 3.5 |
| 💎 Value Gem | ROI > 5.5 and FDR <= 2.5 |
| 🏆 Premium | Points > 160 and FDR <= 2.5 |
| ⚠️ Sell Candidate | Price fall pressure detected |
| ⚖️ Stable | Default fallback |

---

## Testing

Pure analytical functions in `analytics.py` (Z-score, ROI, price prediction, FDR labelling, and the price pressure confidence interval) are covered by unit tests in `tests/test_analytics.py`.

```bash
pip install pytest --break-system-packages
pytest tests/ -v
```

`conftest.py` (an empty file at the project root) ensures pytest can resolve the `fpl_engine` package when run from the project root.

---

## Known Issues & Limitations

- **Off-season data:** During the FPL off-season, `transfers_in_event` and `form` are 0 for every player. As a result, Z-score, price change pressure, the confidence interval, and Captain Score formulas may show flat or 0.0 values — this is the mathematically correct output for zero-variance/zero-activity input, not a bug. These metrics become meaningful again once the season is underway and transfer/form activity varies between players.
- **Player photos:** `scrape_photos.py` must be run once before first use. If new players are added to the FPL API after the last scrape (e.g. transfers, promotions), their photos may be missing until the script is re-run. A generic placeholder is shown via the `onerror` fallback for any missing image.
- **Transfers-out estimate:** The FPL API does not expose `transfers_out` directly, so it is estimated as 30% of `transfers_in`. The confidence interval quantifies uncertainty in this specific assumption, but does not correct for any systematic bias in the 30% figure itself.

---

## Author

Built as a coursework project (Programming in Python 2). 
Data sourced for educational purposes only.
![Demo](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExazR1bHY0eGFiMmc2eTB2eGFjbzVlbm5wbTlqa2wwMXpjdTFjYjlkZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/qGVfMtQtD2a4QhhUg7/giphy.gif)
