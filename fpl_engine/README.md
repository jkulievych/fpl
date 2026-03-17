# FPL Hype Tracker

A web-based analytics dashboard for Fantasy Premier League, built with Python and Flask.
Connects to the official FPL API, applies statistical models, and presents insights through interactive visualisations.

**Course:** Programming in Python 2 — Social Data Science

---

## How to Run

```bash
pip install flask flask-sqlalchemy pandas plotly textblob requests beautifulsoup4
python scrape_photos.py   # one time only — downloads player photos
python app.py
```

Open `http://localhost:5000` in your browser. The database populates automatically on first load.

---

## Project Structure

```
python2project2/
├── app.py                  # Flask routes and application logic
├── database.db             # SQLite database (auto-generated)
├── scrape_photos.py        # One-time player photo downloader
├── fpl_engine/
│   ├── models.py           # SQLAlchemy Player model
│   ├── api_client.py       # FPL API integration + caching
│   ├── analytics.py        # Z-score, ROI, FDR, price prediction
│   └── scraper.py          # News scraper + sentiment analysis
├── static/
│   └── player_photos/      # Locally cached player images
└── templates/
    ├── index.html          # Main dashboard
    └── player.html         # Player detail page
```

---

## Data Source

All data comes from the official FPL REST API (no authentication required).

**Main endpoint:**
```
GET https://fantasy.premierleague.com/api/bootstrap-static/
```
Returns all player data: name, price, transfers, points, goals, assists, position, form.

**Fixtures endpoint:**
```
GET https://fantasy.premierleague.com/api/fixtures/
```
Returns all season fixtures with difficulty ratings (1–5) used for the FDR analysis.

**Caching:** The API is only called if the database data is older than one hour, checked via the `last_updated` timestamp on the Player model.

---

## Analytical Methodology

### Z-Score (Market Hype Index)

Measures how many standard deviations a player's transfer activity is above or below the league average. Calculated across all ~700 players each session.

```
Z = (transfers_in - mean) / standard_deviation
```

- Z > 3.0 — extreme anomaly, viral hype
- Z 1–3 — above average interest
- Z < 0 — player being ignored or sold

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

## Features

**Dashboard**
- Player table with Z-score, ROI, form, and price
- Position filter (GK / DEF / MID / FWD)
- Budget slider filtering by max price
- Interactive bubble chart (price vs transfers, coloured by ROI)
- Sentiment-analysed news headlines

**Player Page**
- Hero card with photo, team badge, and fixture difficulty
- AI verdict card
- Radar chart vs league averages
- Stats grid and price change prediction bar
