from flask import Flask, render_template
from fpl_engine.api_client import get_fpl_data  # Імпортуємо твій "двигун"

app = Flask(__name__)


@app.route('/')
def index():
    players_df = get_fpl_data()

    if players_df is not None:
        # Сортуємо за кількістю трансферів (найбільший хайп зверху)
        top_hyped = players_df.sort_values(by='transfers_in_event', ascending=False).head(10)
        # Перетворюємо в список словників для HTML
        players_list = top_hyped.to_dict('records')
    else:
        players_list = []

    return render_template('index.html', players=players_list)


if __name__ == '__main__':
    app.run(debug=True)