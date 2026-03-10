import requests
import pandas as pd
from fpl_engine.models import db, Player

def get_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['elements'])

        # Вибираємо потрібні колонки
        columns = ['id', 'first_name', 'second_name', 'now_cost',
                   'selected_by_percent', 'transfers_in_event',
                   'total_points', 'goals_scored', 'assists']
        df = df[columns]

        # Перейменовуємо колонки (тепер transfers_in_event стає transfers_in)
        df = df.rename(columns={
            'transfers_in_event': 'transfers_in',
            'goals_scored': 'goals'
        })

        # Коригуємо ціну (в API вона вказана в одиницях х10)
        df['now_cost'] = df['now_cost'] / 10
        return df
    return None

def update_db_from_api():
    df = get_fpl_data()
    if df is None:
        return False

    for _, row in df.iterrows():
        # Шукаємо гравця в базі за ID
        player = Player.query.get(row['id'])

        if not player:
            # Створюємо нового гравця, якщо його ще немає в базі
            player = Player(id=row['id'])
            db.session.add(player)

        # ОНОВЛЮЄМО ВСІ ПОЛЯ (використовуємо нові назви з DataFrame)
        player.first_name = row['first_name']
        player.second_name = row['second_name']
        player.now_cost = row['now_cost']
        player.transfers_in = row['transfers_in']  # ТУТ БУЛА ПОМИЛКА (виправлено)
        player.selected_by_percent = float(row['selected_by_percent'])

        # Додаємо нову статистику для ROI
        player.total_points = row['total_points']
        player.goals = row['goals']
        player.assists = row['assists']

    db.session.commit()
    return True