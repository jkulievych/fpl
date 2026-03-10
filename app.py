import os
import pandas as pd
from flask import Flask, render_template
from fpl_engine.models import db, Player # Наш новий імпорт
from fpl_engine.api_client import get_fpl_data, update_db_from_api # Додай імпорт
from fpl_engine.scraper import get_football_news # Новий імпорт
from fpl_engine.analytics import get_sentiment, calculate_hype_metrics # Новий імпорт
from fpl_engine.analytics import create_hype_chart # Додай імпорт
from flask import Flask, render_template, request # Додай request
from sqlalchemy import or_
from fpl_engine.analytics import create_interactive_chart # Додай імпорт

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
    # 1. Синхронізація
    update_db_from_api()
    query = request.args.get('q')

    all_players = Player.query.all()
    if not all_players:
        return render_template('index.html', players=[], news=[], avg=0, limit=0, plot=None)

    # 2. DataFrame на основі ВСІХ гравців ліги (для коректної статистики)
    all_df = pd.DataFrame([{
        'id': p.id,
        'first_name': p.first_name,
        'second_name': p.second_name,
        'transfers_in': p.transfers_in,
        'now_cost': p.now_cost,
        'total_points': p.total_points,
        'selected_by_percent': p.selected_by_percent
    } for p in all_players])

    from fpl_engine.analytics import calculate_z_score, calculate_roi, create_interactive_chart

    # Розраховуємо статистику по всій лізі, щоб std != 0
    all_df = calculate_z_score(all_df)
    all_df = calculate_roi(all_df)

    avg_transfers = all_df['transfers_in'].mean()
    hype_limit = all_df['transfers_in'].quantile(0.95)

    # 3. Фільтрація для ТАБЛИЦІ (результати пошуку)
    if query:
        players_to_show = Player.query.filter(
            or_(Player.first_name.ilike(f'%{query}%'), Player.second_name.ilike(f'%{query}%'))
        ).all()
    else:
        players_to_show = Player.query.order_by(Player.transfers_in.desc()).limit(15).all()

    # Мапимо розраховані Z-score та ROI назад до об'єктів таблиці
    for p in players_to_show:
        row = all_df.loc[all_df['id'] == p.id]
        if not row.empty:
            p.z_score = round(row['z_score'].values[0], 2)
            p.roi = round(row['roi'].values[0], 2)

    # 4. ПІДГОТОВКА ГРАФІКА (Топ-50 для масштабу та контексту)
    top_50_for_chart = all_df.sort_values(by='transfers_in', ascending=False).head(50).copy()

    # Додаємо мітку підсвітки обраного гравця
    top_50_for_chart['is_selected'] = False
    if query:
        search_ids = [p.id for p in players_to_show]
        top_50_for_chart.loc[top_50_for_chart['id'].isin(search_ids), 'is_selected'] = True

    # Примусова конвертація для Plotly
    for col in ['now_cost', 'transfers_in', 'roi', 'z_score']:
        top_50_for_chart[col] = pd.to_numeric(top_50_for_chart[col], errors='coerce').fillna(0)

    graph_json = create_interactive_chart(top_50_for_chart)

    # 5. Media Sentiment Mapping (Скрапінг та аналіз тональності)
    raw_news = get_football_news()
    analyzed_news = []

    # Робимо аналіз тільки якщо новини є
    if raw_news:
        for news_item in raw_news:
            sentiment = get_sentiment(news_item)
            # Шукаємо, чи згадується хтось із гравців у новині
            matched_player = next((f"{p.first_name} {p.second_name}" for p in players_to_show
                                   if p.second_name.lower() in news_item.lower()), None)
            analyzed_news.append({
                'text': news_item,
                'sentiment': round(sentiment, 2),
                'mood': "😊" if sentiment > 0.1 else "☹️" if sentiment < -0.1 else "😐",
                'player_tag': matched_player
            })

    return render_template('index.html',
                           players=players_to_show,
                           news=analyzed_news,
                           avg=round(avg_transfers, 1),
                           limit=round(hype_limit, 1),
                           plot=graph_json,
                           query=query)


if __name__ == '__main__':
    app.run(debug=True)