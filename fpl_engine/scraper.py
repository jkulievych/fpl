import requests
from bs4 import BeautifulSoup


def get_football_news():
    url = "https://www.bbc.com/sport/football"
    response = requests.get(url)
    news_list = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Шукаємо заголовки (на BBC це зазвичай теги h3)
        headings = soup.find_all('h3')

        for h in headings:
            title = h.get_text().strip()
            if title and len(title) > 10:  # Відсікаємо занадто короткі фрази
                news_list.append(title)

    return news_list[:10]  # Беремо перші 10 новин