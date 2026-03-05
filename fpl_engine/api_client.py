import requests
import pandas as pd


def get_fpl_data():
    # Посилання на основні дані FPL
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        # Створюємо DataFrame з гравцями
        df = pd.DataFrame(data['elements'])

        # Вибираємо тільки потрібні нам колонки
        columns_to_keep = [
            'first_name', 'second_name', 'now_cost',
            'selected_by_percent', 'transfers_in_event', 'form'
        ]
        df = df[columns_to_keep]

        # Виправляємо ціну (в API вона помножена на 10, наприклад 125 замість 12.5)
        df['now_cost'] = df['now_cost'] / 10

        return df
    else:
        return None