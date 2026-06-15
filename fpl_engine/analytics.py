from textblob import TextBlob
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import os
import plotly.utils
import json
import plotly.graph_objects as go
import requests
import numpy as np
matplotlib.use('Agg')


def get_sentiment(text):
    analysis = TextBlob(text)
    return analysis.sentiment.polarity


def calculate_hype_metrics(players_df):
    if players_df is None or players_df.empty:
        return None
    mean_transfers = players_df['transfers_in'].mean()
    hype_threshold = players_df['transfers_in'].quantile(0.9)
    players_df['is_hyped'] = players_df['transfers_in'] > hype_threshold
    return players_df, mean_transfers, hype_threshold


def create_hype_chart(players_df, static_path):
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    plot = sns.scatterplot(
        data=players_df,
        x='now_cost',
        y='transfers_in',
        size='selected_by_percent',
        hue='selected_by_percent',
        palette='viridis'
    )
    plt.title('Hype (Transfers) vs Cost')
    chart_path = os.path.join(static_path, 'hype_chart.png')
    plt.savefig(chart_path)
    plt.close()
    return 'hype_chart.png'


def calculate_z_score(df):
    mean_val = df['transfers_in'].mean()
    std_val = df['transfers_in'].std()
    if std_val == 0:
        df['z_score'] = 0.0
        return df
    df['z_score'] = (df['transfers_in'] - mean_val) / std_val
    return df


def calculate_roi(df):
    df['roi'] = df['total_points'] / df['now_cost']
    return df


def predict_price_change(player_transfers_in, player_transfers_out, total_players=8000000):
    """
    Predicts whether a player's price will rise, fall, or stay the same.

    FPL price change logic:
    - Each player has a hidden 'price change score' that accumulates over time
    - Price RISES when net transfers in exceed ~1% of total FPL managers
    - Price FALLS when net transfers out exceed ~1% of total FPL managers
    - Price changes by £0.1m at a time

    Returns a dict with prediction, net transfers, and threshold info.
    """
    # FPL threshold: roughly 1% of all managers triggers a price change
    threshold = total_players * 0.01  # ~80,000 net transfers

    net = player_transfers_in - player_transfers_out

    # Calculate how close the player is to a price change (as a percentage)
    pressure = round((abs(net) / threshold) * 100, 1)
    pressure = min(pressure, 100)  # cap at 100%

    if net > threshold:
        prediction = "rise"
        label = "📈 PRICE RISE"
        detail = f"Net +{net:,} transfers. {pressure}% toward £0.1m rise."
        color = "green"
    elif net < -threshold:
        prediction = "fall"
        label = "📉 PRICE FALL"
        detail = f"Net {net:,} transfers. {pressure}% toward £0.1m drop."
        color = "red"
    elif net > 0:
        prediction = "stable_rising"
        label = "🔼 SLIGHT PRESSURE UP"
        detail = f"Net +{net:,} transfers. {pressure}% toward a rise — not there yet."
        color = "yellow"
    elif net < 0:
        prediction = "stable_falling"
        label = "🔽 SLIGHT PRESSURE DOWN"
        detail = f"Net {net:,} transfers. {pressure}% toward a fall — monitor closely."
        color = "yellow"
    else:
        prediction = "stable"
        label = "➡️ STABLE"
        detail = "No significant transfer pressure in either direction."
        color = "neutral"

    return {
        'prediction': prediction,
        'label': label,
        'detail': detail,
        'color': color,
        'net': net,
        'pressure': pressure
    }


def get_fixture_difficulty(team_code):
    """
    Fetches next 5 fixtures for a team and returns average difficulty (1-5).
    Lower = easier, Higher = harder.
    """
    try:
        bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
        teams = {t['code']: t['id'] for t in bootstrap['teams']}
        team_id = teams.get(team_code)
        if not team_id:
            return 3.0

        fixtures = requests.get("https://fantasy.premierleague.com/api/fixtures/").json()

        upcoming = []
        for f in fixtures:
            if f['finished']:
                continue
            if f['team_h'] == team_id:
                upcoming.append(f['team_h_difficulty'])
            elif f['team_a'] == team_id:
                upcoming.append(f['team_a_difficulty'])
            if len(upcoming) == 5:
                break

        if not upcoming:
            return 3.0

        return round(sum(upcoming) / len(upcoming), 2)

    except Exception:
        return 3.0


def get_fixture_label(avg_difficulty):
    if avg_difficulty <= 2.0:
        return "🟢 EASY", "green"
    elif avg_difficulty <= 3.0:
        return "🟡 MODERATE", "yellow"
    else:
        return "🔴 TOUGH", "red"


def create_interactive_chart(df):
    if df is None or df.empty:
        return "{}"

    x_cost = pd.to_numeric(df['now_cost'], errors='coerce').fillna(0).tolist()
    y_transfers = pd.to_numeric(df['transfers_in'], errors='coerce').fillna(0).tolist()

    names = df['second_name'].astype(str).tolist()
    first_names = df['first_name'].astype(str).tolist()
    full_names = [f"{f} {s}" for f, s in zip(first_names, names)]

    roi = pd.to_numeric(df['roi'], errors='coerce').fillna(0).tolist()
    z_score = pd.to_numeric(df['z_score'], errors='coerce').fillna(0).tolist()
    pts = pd.to_numeric(df['total_points'], errors='coerce').fillna(0).tolist()
    selected = pd.to_numeric(df['selected_by_percent'], errors='coerce').fillna(0).tolist()

    bubble_sizes = [8 + (s * 1.5) for s in selected]
    custom_data = list(zip(full_names, roi, z_score, pts, selected))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_cost,
        y=y_transfers,
        mode='markers',
        customdata=custom_data,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br><br>" +
            "Cost: £%{x}m<br>" +
            "Transfers In: %{y:,}<br>" +
            "ROI (Efficiency): %{customdata[1]:.2f}<br>" +
            "Z-Score (Hype): %{customdata[2]:.2f}<br>" +
            "Total Points: %{customdata[3]}<br>" +
            "Ownership: %{customdata[4]}%<br>" +
            "<extra></extra>"
        ),
        marker=dict(
            size=bubble_sizes,
            color=roi,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="ROI"),
            line=dict(width=1, color='DarkSlateGrey')
        )
    ))

    fig.update_layout(
        title='Market Pulse: Hype vs Reality',
        xaxis_title='Player Cost (£m)',
        yaxis_title='Weekly Transfers In',
        template='plotly_white',
        hovermode='closest'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def optimise_team(players, metric='total_points', budget=100.0):
    """
    Solves the FPL team selection problem using linear programming.

    Constraints:
    - Exactly 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)
    - Total cost <= budget
    - Max 3 players from the same team

    Parameters:
        players: list of Player model objects
        metric: 'total_points', 'form', or 'roi'
        budget: max spend in millions (default 100.0)

    Returns:
        dict with selected players grouped by position, total cost, total score
    """
    try:
        import pulp
    except ImportError:
        return {'error': 'pulp not installed. Run: pip install pulp'}

    # Position maps
    pos_names = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    pos_limits = {1: 2, 2: 5, 3: 5, 4: 3}

    # Build score map based on chosen metric
    def get_score(p):
        if metric == 'form':
            return float(p.form) if p.form else 0.0
        elif metric == 'roi':
            return round(p.total_points / p.now_cost, 4) if p.now_cost else 0.0
        else:
            return float(p.total_points)

    # Filter out players with missing data
    valid = [p for p in players if p.element_type in pos_names and p.now_cost and p.now_cost > 0]

    # Create the LP problem — maximise total score
    prob = pulp.LpProblem("FPL_Team_Optimiser", pulp.LpMaximize)

    # Binary decision variable: 1 = selected, 0 = not selected
    selected = {p.id: pulp.LpVariable(f"p_{p.id}", cat='Binary') for p in valid}

    # Objective: maximise total score
    prob += pulp.lpSum(get_score(p) * selected[p.id] for p in valid)

    # Constraint 1: total cost <= budget
    prob += pulp.lpSum(p.now_cost * selected[p.id] for p in valid) <= budget

    # Constraint 2: exactly 15 players total
    prob += pulp.lpSum(selected[p.id] for p in valid) == 15

    # Constraint 3: position limits
    for pos, limit in pos_limits.items():
        prob += pulp.lpSum(selected[p.id] for p in valid if p.element_type == pos) == limit

    # Constraint 4: max 3 from same team
    team_codes = set(p.team_code for p in valid)
    for team in team_codes:
        prob += pulp.lpSum(selected[p.id] for p in valid if p.team_code == team) <= 3

    # Solve (suppress output)
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != 'Optimal':
        return {'error': 'Could not find an optimal solution. Try increasing the budget.'}

    # Extract selected players
    chosen = [p for p in valid if pulp.value(selected[p.id]) == 1]

    # Group by position
    grouped = {name: [] for name in pos_names.values()}
    for p in chosen:
        pos = pos_names[p.element_type]
        grouped[pos].append({
            'id': p.id,
            'name': f"{p.first_name} {p.second_name}",
            'team_code': p.team_code,
            'cost': p.now_cost,
            'total_points': p.total_points,
            'form': float(p.form) if p.form else 0.0,
            'roi': round(p.total_points / p.now_cost, 2) if p.now_cost else 0,
            'photo': p.photo,
        })

    total_cost = round(sum(p.now_cost for p in chosen), 1)
    total_points = sum(p.total_points for p in chosen)
    total_score = round(sum(get_score(p) for p in chosen), 2)

    return {
        'players': grouped,
        'total_cost': total_cost,
        'total_points': total_points,
        'total_score': total_score,
        'metric': metric,
        'budget': budget,
        'error': None
    }

def calculate_price_pressure_ci(player_transfers_in, total_players=8000000, n_samples=2000):
    """
    Monte Carlo 95% confidence interval for price change pressure.

    The transfers_out figure isn't exposed by the FPL API, so the app
    estimates it as ~30% of transfers_in. That ratio is uncertain — this
    treats it as a random variable (Normal, mean=0.30, sd=0.08, clipped
    to [0.05, 0.60]) and recomputes the pressure percentage for many
    sampled ratios, returning the 2.5th and 97.5th percentiles.
    """
    threshold = total_players * 0.01
    rng = np.random.default_rng()
    ratios = np.clip(rng.normal(0.30, 0.08, n_samples), 0.05, 0.60)

    transfers_out = player_transfers_in * ratios
    net = player_transfers_in - transfers_out
    pressures = np.minimum(np.abs(net) / threshold * 100, 100)

    return {
        'ci_low': round(float(np.percentile(pressures, 2.5)), 1),
        'ci_high': round(float(np.percentile(pressures, 97.5)), 1),
    }

def calculate_captain_score(form, fixture_avg):
    """
    Higher score = stronger captaincy pick.
    Combines recent form with upcoming fixture ease (1=easy, 5=hard).
    """
    fixture_factor = (6 - fixture_avg) / 5
    return round(form * fixture_factor, 2)


def get_team_fixture_map():
    """
    Fetches each team's average difficulty for their next 5 fixtures,
    once for all 20 teams — avoids calling the API per-player.
    """
    try:
        bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
        fixtures = requests.get("https://fantasy.premierleague.com/api/fixtures/").json()
        team_code_to_id = {t['code']: t['id'] for t in bootstrap['teams']}
        fixture_map = {}

        for code, team_id in team_code_to_id.items():
            upcoming = []
            for f in fixtures:
                if f['finished']:
                    continue
                if f['team_h'] == team_id:
                    upcoming.append(f['team_h_difficulty'])
                elif f['team_a'] == team_id:
                    upcoming.append(f['team_a_difficulty'])
                if len(upcoming) == 5:
                    break
            fixture_map[code] = round(sum(upcoming) / len(upcoming), 2) if upcoming else 3.0

        return fixture_map
    except Exception:
        return {}