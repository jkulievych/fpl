import requests
import pandas as pd
from datetime import datetime, timedelta
from fpl_engine.models import db, Player

CACHE_DURATION = timedelta(hours=1)  # ── how often to refresh

def _should_refresh():
    """Check if any player was updated more than 1 hour ago."""
    latest = Player.query.order_by(Player.last_updated.desc()).first()
    if not latest:
        return True  # empty DB, definitely fetch
    return datetime.utcnow() - latest.last_updated > CACHE_DURATION

def get_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['elements'])

        columns = ['id', 'first_name', 'second_name', 'now_cost',
                   'selected_by_percent', 'transfers_in_event',
                   'total_points', 'goals_scored', 'assists',
                   'photo', 'team_code', 'form', 'element_type']
        df = df[columns]

        df = df.rename(columns={
            'transfers_in_event': 'transfers_in',
            'goals_scored': 'goals'
        })

        df['now_cost'] = df['now_cost'] / 10
        df['form'] = pd.to_numeric(df['form'], errors='coerce').fillna(0.0)
        return df
    return None

def update_db_from_api():
    # ── NEW: skip if data is fresh ──
    if not _should_refresh():
        print("Cache is fresh, skipping API call.")
        return True

    print("Cache expired, fetching from FPL API...")
    df = get_fpl_data()
    if df is None:
        return False

    for _, row in df.iterrows():
        player = Player.query.get(row['id'])
        if not player:
            player = Player(id=row['id'])
            db.session.add(player)

        player.first_name = row['first_name']
        player.second_name = row['second_name']
        player.now_cost = row['now_cost']
        player.transfers_in = row['transfers_in']
        player.selected_by_percent = float(row['selected_by_percent'])
        player.total_points = row['total_points']
        player.goals = row['goals']
        player.assists = row['assists']
        player.photo = str(row['photo'])
        player.team_code = row['team_code']
        player.form = float(row['form'])
        player.element_type = int(row['element_type'])
        player.last_updated = datetime.utcnow()  # ── NEW: stamp the time

    db.session.commit()
    print(f"DB updated at {datetime.utcnow()}")
    return True