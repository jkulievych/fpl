import os
import pandas as pd
import json
import plotly
import plotly.graph_objects as go
import requests
from flask import Flask, render_template, request
from sqlalchemy import or_
from fpl_engine.models import db, Player
from fpl_engine.api_client import get_fpl_data, update_db_from_api
from fpl_engine.scraper import get_football_news
from fpl_engine.analytics import (
    get_sentiment, calculate_hype_metrics, create_hype_chart,
    create_interactive_chart, calculate_z_score, calculate_roi,
    get_fixture_difficulty, get_fixture_label, predict_price_change,
    optimise_team
)

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


def get_next_deadline():
    try:
        data = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for event in data['events']:
            deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00'))
            if deadline > now:
                return {'gameweek': event['id'], 'deadline': event['deadline_time']}
    except Exception:
        pass
    return None


def get_gameweek_history(player_id):
    """
    Fetches gameweek-by-gameweek points history from FPL API.
    Returns Plotly JSON string or None if unavailable.
    """
    try:
        url = f"https://fantasy.premierleague.com/api/element-summary/{player_id}/"
        data = requests.get(url, timeout=8).json()
        history = data.get('history', [])

        if not history:
            return None

        gameweeks = [h['round'] for h in history]
        points    = [h['total_points'] for h in history]
        goals     = [h['goals_scored'] for h in history]
        assists   = [h['assists'] for h in history]
        minutes   = [h['minutes'] for h in history]

        hover = [
            f"GW{gw}<br>Points: {pt}<br>Goals: {g}<br>Assists: {a}<br>Minutes: {m}"
            for gw, pt, g, a, m in zip(gameweeks, points, goals, assists, minutes)
        ]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=gameweeks,
            y=points,
            mode='lines+markers',
            name='Points',
            line=dict(color='#1f6feb', width=2),
            marker=dict(size=6, color='#388bfd'),
            hovertext=hover,
            hoverinfo='text'
        ))

        # Red X for gameweeks where player didn't play
        blank_gws = [gw for gw, m in zip(gameweeks, minutes) if m == 0]
        blank_pts = [pt for pt, m in zip(points, minutes) if m == 0]
        if blank_gws:
            fig.add_trace(go.Scatter(
                x=blank_gws,
                y=blank_pts,
                mode='markers',
                name='Did not play',
                marker=dict(size=8, color='#f85149', symbol='x'),
                hoverinfo='skip'
            ))

        fig.update_layout(
            xaxis=dict(
                title='Gameweek',
                tickmode='linear',
                dtick=1,
                gridcolor='#21262d',
                zerolinecolor='#30363d',
                color='#8b949e'
            ),
            yaxis=dict(
                title='Points',
                gridcolor='#21262d',
                zerolinecolor='#30363d',
                color='#8b949e'
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8b949e', family='Barlow, sans-serif'),
            legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='#30363d', borderwidth=1),
            margin=dict(l=40, r=20, t=20, b=40),
            height=280,
            hovermode='x unified'
        )

        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    except Exception as e:
        print(f"Gameweek history error: {e}")
        return None


@app.route('/')
def index():
    update_db_from_api()
    query = request.args.get('q')
    position = request.args.get('pos', 'all')

    all_players = Player.query.all()
    if not all_players:
        return render_template('index.html', players=[], news=[], avg=0, limit=0, plot=None)

    all_df = pd.DataFrame([{
        'id': p.id,
        'first_name': p.first_name,
        'second_name': p.second_name,
        'transfers_in': p.transfers_in,
        'now_cost': p.now_cost,
        'total_points': p.total_points,
        'selected_by_percent': p.selected_by_percent
    } for p in all_players])

    all_df = calculate_z_score(all_df)
    all_df = calculate_roi(all_df)

    best_roi_idx = all_df['roi'].idxmax()
    best_roi_player = all_df.loc[best_roi_idx]
    roi_display = f"{best_roi_player['first_name']} {best_roi_player['second_name']}"

    best_hype_idx = all_df['z_score'].idxmax()
    best_hype_player = all_df.loc[best_hype_idx]
    hype_display = f"{best_hype_player['first_name']} {best_hype_player['second_name']}"
    total_count = len(all_df)

    avg_transfers = all_df['transfers_in'].mean()
    hype_limit = all_df['transfers_in'].quantile(0.95)

    player_query = Player.query
    if query:
        player_query = player_query.filter(
            or_(Player.first_name.ilike(f'%{query}%'), Player.second_name.ilike(f'%{query}%'))
        )
    if position != 'all':
        pos_map = {'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
        if position in pos_map:
            player_query = player_query.filter(Player.element_type == pos_map[position])

    players_to_show = player_query.order_by(Player.transfers_in.desc()).limit(20).all()

    for p in players_to_show:
        row = all_df.loc[all_df['id'] == p.id]
        if not row.empty:
            p.z_score = round(row['z_score'].values[0], 2)
            p.roi = round(row['roi'].values[0], 2)

    top_50_for_chart = all_df.sort_values(by='transfers_in', ascending=False).head(50).copy()
    top_50_for_chart['is_selected'] = False
    if query:
        search_ids = [p.id for p in players_to_show]
        top_50_for_chart.loc[top_50_for_chart['id'].isin(search_ids), 'is_selected'] = True

    for col in ['now_cost', 'transfers_in', 'roi', 'z_score']:
        top_50_for_chart[col] = pd.to_numeric(top_50_for_chart[col], errors='coerce').fillna(0)

    graph_json = create_interactive_chart(top_50_for_chart)

    raw_news = get_football_news()
    analyzed_news = []
    if raw_news:
        for item in raw_news:
            sentiment = get_sentiment(item['text'])
            matched_player = next((f"{p.first_name} {p.second_name}" for p in players_to_show
                                   if p.second_name.lower() in item['text'].lower()), None)
            analyzed_news.append({
                'text': item['text'],
                'url': item['url'],
                'sentiment': round(sentiment, 2),
                'mood': "😊" if sentiment > 0.1 else "☹️" if sentiment < -0.1 else "😐",
                'player_tag': matched_player
            })

    deadline_info = get_next_deadline()

    return render_template('index.html',
                           players=players_to_show,
                           news=analyzed_news,
                           avg=round(avg_transfers, 1),
                           limit=round(hype_limit, 1),
                           plot=graph_json,
                           top_efficiency=roi_display,
                           market_anomaly=hype_display,
                           total_db=total_count,
                           query=query,
                           position=position,
                           deadline=deadline_info)


@app.route('/player/<int:player_id>')
def player_page(player_id):
    player = Player.query.get_or_404(player_id)

    all_players = Player.query.all()
    all_df = pd.DataFrame([{
        'id': p.id,
        'transfers_in': p.transfers_in,
        'now_cost': p.now_cost,
        'total_points': p.total_points,
        'goals': p.goals,
        'assists': p.assists
    } for p in all_players])

    all_df = calculate_z_score(all_df)
    all_df = calculate_roi(all_df)

    player_data = all_df.loc[all_df['id'] == player.id]
    if not player_data.empty:
        player.z_score = round(float(player_data['z_score'].values[0]), 2)
        player.roi = round(float(player_data['roi'].values[0]), 2)
    else:
        player.z_score, player.roi = 0, 0

    fixture_avg = get_fixture_difficulty(player.team_code)
    fixture_label, fixture_color = get_fixture_label(fixture_avg)

    estimated_transfers_out = round(player.transfers_in * 0.3)
    price_change = predict_price_change(player.transfers_in, estimated_transfers_out)

    # GAMEWEEK HISTORY CHART
    history_chart = get_gameweek_history(player_id)

    avg_goals = all_df['goals'].mean()
    avg_assists = all_df['assists'].mean()
    avg_roi = all_df['roi'].mean()

    categories = ['Goals', 'Assists', 'Points (scaled)', 'Efficiency (ROI)', 'Market Hype (Z)']

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[player.goals, player.assists, player.total_points / 10, player.roi, player.z_score],
        theta=categories, fill='toself', name=player.second_name,
        line_color='#1f6feb'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[avg_goals, avg_assists, all_df['total_points'].mean() / 10, avg_roi, 0],
        theta=categories, fill='toself', name='League Average',
        line_color='rgba(139, 148, 158, 0.4)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=False)),
        showlegend=True,
        margin=dict(l=40, r=40, t=20, b=20),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    radar_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    rising = price_change['prediction'] in ('rise', 'stable_rising')
    falling = price_change['prediction'] in ('fall', 'stable_falling')

    if player.z_score > 3.0 and fixture_avg > 3.5:
        verdict = "⚠️ RISKY HYPE: Massive demand but tough fixtures ahead. Could disappoint."
    elif player.z_score > 3.0 and fixture_avg <= 2.5 and rising:
        verdict = "🔥 HOT PICK: Huge demand, easy fixtures AND price rising — buy before it's too late."
    elif player.z_score > 3.0 and fixture_avg <= 2.5:
        verdict = "🔥 HOT PICK: Huge demand AND easy fixtures — strong captain candidate."
    elif player.z_score > 3.0:
        verdict = "🔥 HYPED: Anomalous demand. Fixtures are moderate — proceed with caution."
    elif player.roi > 5.5 and fixture_avg <= 2.5 and rising:
        verdict = "💎 VALUE GEM: Best time to buy — great efficiency, easy fixtures, price rising."
    elif player.roi > 5.5 and fixture_avg <= 2.5:
        verdict = "💎 VALUE GEM: Incredible efficiency with easy games coming — buy now."
    elif player.roi > 5.5 and fixture_avg > 3.5:
        verdict = "💎 VALUE GEM: Great efficiency but tough run ahead — hold with caution."
    elif player.roi > 5.5:
        verdict = "💎 VALUE GEM: Excellent points-per-pound ratio. Good moderate fixture run."
    elif player.total_points > 160 and fixture_avg <= 2.5:
        verdict = "🏆 PREMIUM: Elite performer with a great fixture run — essential pick."
    elif player.total_points > 160 and fixture_avg > 3.5:
        verdict = "🏆 PREMIUM: Elite performer but difficult fixtures ahead — consider alternatives."
    elif player.total_points > 160:
        verdict = "🏆 PREMIUM: One of the league's best performers with manageable fixtures."
    elif falling:
        verdict = "⚠️ SELL CANDIDATE: Transfer activity suggests a price drop is coming."
    else:
        verdict = "⚖️ STABLE: Reliable rotation option."

    return render_template('player.html',
                           player=player,
                           verdict=verdict,
                           radar_plot=radar_json,
                           fixture_avg=fixture_avg,
                           fixture_label=fixture_label,
                           fixture_color=fixture_color,
                           price_change=price_change,
                           history_chart=history_chart)


@app.route('/optimiser', methods=['GET', 'POST'])
def optimiser():
    result = None
    metric = 'total_points'
    budget = 100.0

    if request.method == 'POST':
        metric = request.form.get('metric', 'total_points')
        try:
            budget = float(request.form.get('budget', 100.0))
        except ValueError:
            budget = 100.0

        all_players = Player.query.all()
        result = optimise_team(all_players, metric=metric, budget=budget)

    return render_template('optimiser.html',
                           result=result,
                           metric=metric,
                           budget=budget)


if __name__ == '__main__':
    app.run(debug=True)