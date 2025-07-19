import requests
import os


def search_youtube(track_title, artist):
    api_key = os.getenv("YOUTUBE_API_KEY")
    query = f"{track_title} {artist} audio"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={api_key}&maxResults=1&type=video"
    resp = requests.get(url)
    items = resp.json().get("items", [])
    if items:
        video_id = items[0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
    return None
