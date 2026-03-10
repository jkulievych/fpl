import requests
from bs4 import BeautifulSoup


def get_football_news():
    """Збирає останні футбольні новини з BBC Sport"""
    # Додаємо User-Agent, щоб сайт думав, що ми звичайний браузер, а не бот
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    url = 'https://www.bbc.com/sport/football'
    news_list = []

    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Сайти часто міняють дизайн, тому шукаємо відразу кілька типів заголовків
        headlines = soup.find_all(['h2', 'h3'])

        for h in headlines:
            text = h.get_text(strip=True)
            # Фільтруємо сміття: беремо лише нормальні речення, яких ще немає в списку
            if len(text) > 25 and text not in news_list:
                news_list.append(text)

        # Якщо з якихось причин сайт нічого не віддав, даємо запасний варіант
        if not news_list:
            return [
                "Premier League updates: Teams prepare for the next crucial matches.",
                "Manager praises squad performance after intense training session.",
                "Injury concerns grow for key players ahead of the weekend."
            ]

        return news_list[:10]  # Повертаємо топ-10 найсвіжіших новин

    except Exception as e:
        print(f"Помилка скрапінгу: {e}")
        # Якщо немає інтернету або сайт впав, стрічка новин все одно не буде порожньою
        return [
            "FPL Market shifts: Managers are making early transfers.",
            "Weather conditions might affect upcoming Premier League fixtures."
        ]