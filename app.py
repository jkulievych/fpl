import os
import pandas as pd
from flask import Flask, render_template
from fpl_engine.models import db, Player # Наш новий імпорт
from fpl_engine.api_client import get_fpl_data, update_db_from_api # Додай імпорт
from fpl_engine.scraper import get_football_news # Новий імпорт
from fpl_engine.analytics import get_sentiment, calculate_hype_metrics # Новий імпорт
from fpl_engine.analytics import create_hype_chart # Додай імпорт


app = Flask(__name__)

# Шлях до файлу бази даних у корені проекту
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ініціалізація
db.init_app(app)

# Створення таблиць (виконується один раз при запуску)
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    update_db_from_api()

    # Отримуємо всіх гравців для розрахунків
    all_players = Player.query.all()

    # Перетворюємо в DataFrame для аналітики
    df = pd.DataFrame([{
        'now_cost': p.now_cost,
        'transfers_in': p.transfers_in,
        'selected_by_percent': p.selected_by_percent
    } for p in all_players])

    # Розраховуємо статистику, яку ви вчили (mean, quantile)
    avg_transfers = df['transfers_in'].mean()
    hype_limit = df['transfers_in'].quantile(0.95)  # Топ 5% хайпу

    # Створюємо графік
    create_hype_chart(df.sort_values(by='transfers_in', ascending=False).head(50), app.static_folder)

    players = Player.query.order_by(Player.transfers_in.desc()).limit(15).all()
    news = get_football_news()

    return render_template('index.html', players=players, news=news, avg=avg_transfers, limit=hype_limit)


if __name__ == '__main__':
    app.run(debug=True)