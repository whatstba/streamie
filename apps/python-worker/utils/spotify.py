from dotenv import load_dotenv
load_dotenv()
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials())

def search_tracks(features, limit=10):
    sp = get_spotify_client()
    query = f'genre:"{features["genre"]}"'
    results = sp.search(q=query, type='track', limit=limit)
    tracks = []
    for item in results['tracks']['items']:
        tracks.append({
            "id": item["id"],
            "title": item["name"],
            "artist": item["artists"][0]["name"],
            "uri": item["uri"]
        })
    return tracks

def get_audio_features(track_ids):
    sp = get_spotify_client()
    features = sp.audio_features(track_ids)
    return features 