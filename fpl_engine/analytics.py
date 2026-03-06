from textblob import TextBlob
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import os
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