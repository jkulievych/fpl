import requests, os

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "player_photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)


def download_photos():
    resp = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
    players = resp.json()["elements"]

    for player in players:
        photo_id = player["photo"].replace(".jpg", "")
        save_path = os.path.join(PHOTOS_DIR, f"{photo_id}.png")

        if os.path.exists(save_path):
            print(f"Skipping {player['first_name']}, exists.")
            continue

        url = f"https://resources.premierleague.com/premierleague25/photos/players/110x140/{photo_id}.png"

        headers = {"Referer": "https://www.premierleague.com/"}
        img_resp = requests.get(url, headers=headers)

        if img_resp.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(img_resp.content)
            print(f"Saved: {player['first_name']} {player['second_name']}")
        else:
            print(f"Failed ({img_resp.status_code}): {player['first_name']} {player['second_name']}")


if __name__ == "__main__":
    download_photos()