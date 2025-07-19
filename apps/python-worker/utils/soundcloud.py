import requests
import os


def search_soundcloud(track_title, artist):
    client_id = os.getenv("SOUNDCLOUD_CLIENT_ID")
    query = f"{track_title} {artist}"
    url = f"https://api.soundcloud.com/tracks?client_id={client_id}&q={query}&limit=1"
    resp = requests.get(url)
    tracks = resp.json()
    if tracks:
        return tracks[0].get("permalink_url")
    return None
