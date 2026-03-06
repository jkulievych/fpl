import requests
import pandas as pd
from fpl_engine.models import db, Player


def get_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['elements'])
        # Обов'язково беремо 'id'!
        df = df[['id', 'first_name', 'second_name', 'now_cost', 'selected_by_percent', 'transfers_in_event']]
        df['now_cost'] = df['now_cost'] / 10
        return df
    return None



def update_db_from_api():
    df = get_fpl_data()
    if df is None:
        return False

    for _, row in df.iterrows():
        # Шукаємо гравця в базі за ID
        # (У реальному API ID — це поле 'id', ми його додамо)
        player = Player.query.get(row.get('id'))

        if not player:
            # Якщо гравця немає — створюємо нового
            player = Player(
                id=row.get('id'),
                first_name=row['first_name'],
                second_name=row['second_name'],
                now_cost=row['now_cost'],
                transfers_in=row['transfers_in_event'],
                selected_by_percent=float(row['selected_by_percent'])
            )
            db.session.add(player)
        else:
            # Якщо є — оновлюємо дані
            player.now_cost = row['now_cost']
            player.transfers_in = row['transfers_in_event']
            player.selected_by_percent = float(row['selected_by_percent'])

    db.session.commit()
    return True