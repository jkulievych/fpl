import requests
from bs4 import BeautifulSoup


def get_football_news():
    """
    Fetches Premier League news from RSS feeds.
    Tries multiple sources in order — falls back to next if one fails.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # RSS feeds — more reliable than scraping HTML pages
    sources = [
        'https://www.skysports.com/premier-league',  # Sky Sports Football (PL focused)
        'https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml',  # BBC Sport PL
        'https://www.theguardian.com/football/premierleague/rss',  # Guardian PL
    ]

    news_list = []

    for feed_url in sources:
        try:
            response = requests.get(feed_url, headers=headers, timeout=8)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'xml')

            items = soup.find_all('item')
            if not items:
                # Try html.parser as fallback for non-standard feeds
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.find_all('item')

            for item in items:
                title = item.find('title')
                link  = item.find('link')

                if not title or not link:
                    continue

                text = title.get_text(strip=True)
                url  = link.get_text(strip=True)

                # Skip very short titles (navigation items, etc.)
                if len(text) < 20:
                    continue

                if {'text': text, 'url': url} not in news_list:
                    news_list.append({'text': text, 'url': url})

            if news_list:
                print(f"Scraper: got {len(news_list)} articles from {feed_url}")
                break  # stop if we got results

        except Exception as e:
            print(f"Scraper failed for {feed_url}: {e}")
            continue

    if not news_list:
        print("Scraper: all sources failed, using fallback")
        return _fallback_news()

    return news_list[:16]


def _fallback_news():
    """Static fallback news when all scrapers fail."""
    return [
        {
            'text': 'FPL managers making early moves ahead of next gameweek deadline.',
            'url': 'https://fantasy.premierleague.com'
        },
        {
            'text': 'Price changes expected as transfer activity increases this week.',
            'url': 'https://fantasy.premierleague.com'
        },
        {
            'text': 'Fixture difficulty ratings updated for upcoming Premier League rounds.',
            'url': 'https://fantasy.premierleague.com'
        },
    ]