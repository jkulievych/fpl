from textblob import TextBlob
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import os
import plotly.utils
import json
import plotly.graph_objects as go
matplotlib.use('Agg')


def get_sentiment(text):
    """Визначає емоційне забарвлення тексту від -1 (негатив) до 1 (позитив)"""
    analysis = TextBlob(text)
    return analysis.sentiment.polarity


def calculate_hype_metrics(players_df):
    """Використовуємо статистику з твоїх пар для аналізу"""
    if players_df is None or players_df.empty:
        return None

    # 1. Розраховуємо середню кількість трансферів (mean)
    mean_transfers = players_df['transfers_in'].mean()

    # 2. Розраховуємо квантиль 0.9 (топ-10% найпопулярніших)
    # Це саме те, що ти робила в R: quantile(data, 0.9)
    hype_threshold = players_df['transfers_in'].quantile(0.9)

    # 3. Додаємо мітку: чи є гравець "хайповим"
    players_df['is_hyped'] = players_df['transfers_in'] > hype_threshold

    return players_df, mean_transfers, hype_threshold


def create_hype_chart(players_df, static_path):
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")

    # Робимо графік
    plot = sns.scatterplot(
        data=players_df,
        x='now_cost',
        y='transfers_in',
        size='selected_by_percent',
        hue='selected_by_percent',
        palette='viridis'
    )

    plt.title('Hype (Transfers) vs Cost')

    # Зберігаємо
    chart_path = os.path.join(static_path, 'hype_chart.png')
    plt.savefig(chart_path)
    plt.close()
    return 'hype_chart.png'


def calculate_z_score(df):
    """
    Розраховуємо Z-score для трансферів: (x - mean) / std
    Це показує, на скільки стандартних відхилень гравець популярніший за середнього.
    """
    mean_val = df['transfers_in'].mean()
    std_val = df['transfers_in'].std()

    # Уникаємо ділення на нуль
    if std_val == 0: return 0

    df['z_score'] = (df['transfers_in'] - mean_val) / std_val
    return df

def calculate_roi(df):
    """
    ROI = Total Points / Cost
    Показує ефективність інвестиції в гравця.
    """
    df['roi'] = df['total_points'] / df['now_cost']
    return df


def create_interactive_chart(df):
    if df is None or df.empty:
        return "{}"

    # 1. БЕЗПЕЧНА ЕКСТРАКЦІЯ: Витягуємо всі дані у чисті списки Python
    x_cost = pd.to_numeric(df['now_cost'], errors='coerce').fillna(0).tolist()
    y_transfers = pd.to_numeric(df['transfers_in'], errors='coerce').fillna(0).tolist()

    # Дані для підказок та кольорів
    names = df['second_name'].astype(str).tolist()
    first_names = df['first_name'].astype(str).tolist()
    full_names = [f"{f} {s}" for f, s in zip(first_names, names)]

    roi = pd.to_numeric(df['roi'], errors='coerce').fillna(0).tolist()
    z_score = pd.to_numeric(df['z_score'], errors='coerce').fillna(0).tolist()
    pts = pd.to_numeric(df['total_points'], errors='coerce').fillna(0).tolist()
    selected = pd.to_numeric(df['selected_by_percent'], errors='coerce').fillna(0).tolist()

    # 2. БЕЗПЕЧНИЙ РОЗМІР: Формуємо список розмірів (мінімум 8, плюс бонус за популярність)
    bubble_sizes = [8 + (s * 1.5) for s in selected]

    # 3. Пакуємо всі додаткові дані разом, щоб передати їх у підказку (hover)
    custom_data = list(zip(full_names, roi, z_score, pts, selected))

    # 4. Будуємо графік
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_cost,
        y=y_transfers,
        mode='markers',
        customdata=custom_data,
        # Налаштовуємо красиву підказку при наведенні
        hovertemplate=(
                "<b>%{customdata[0]}</b><br><br>" +
                "Cost: £%{x}m<br>" +
                "Transfers In: %{y:,}<br>" +
                "ROI (Efficiency): %{customdata[1]:.2f}<br>" +
                "Z-Score (Hype): %{customdata[2]:.2f}<br>" +
                "Total Points: %{customdata[3]}<br>" +
                "Ownership: %{customdata[4]}%<br>" +
                "<extra></extra>"  # Прибирає зайве технічне поле поруч з підказкою
        ),
        marker=dict(
            size=bubble_sizes,
            color=roi,  # Колір залежить від ROI
            colorscale='Viridis',  # Красива шкала від фіолетового (погано) до жовтого (супер)
            showscale=True,  # Показуємо легенду кольорів збоку
            colorbar=dict(title="ROI"),
            line=dict(width=1, color='DarkSlateGrey')
        )
    ))

    # 5. Оформлення
    fig.update_layout(
        title='Market Pulse: Hype vs Reality',
        xaxis_title='Player Cost (£m)',
        yaxis_title='Weekly Transfers In',
        template='plotly_white',
        hovermode='closest'
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)



