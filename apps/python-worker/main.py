from dotenv import load_dotenv
load_dotenv() 
from utils.mood_interpreter import interpret_mood
from utils.spotify import search_tracks, get_audio_features
from utils.youtube import search_youtube
from utils.soundcloud import search_soundcloud
from utils.transitions import suggest_transitions
from utils.librosa import run_beat_track

def main():
    # prompt = input("Enter a mood/genre prompt: ")
    # features = interpret_mood(prompt)
    # print(f"Interpreted features: {features}")
    beat_track = run_beat_track()
    print(beat_track)
    # tracks = search_tracks(features, limit=7)
    # track_ids = [t['id'] for t in tracks]
    # audio_features = get_audio_features(track_ids)
    # Merge metadata and features
    # track_features = []
    # for t, f in zip(tracks, audio_features):
    #     if not f: continue
    #     t.update({
    #         "tempo": f["tempo"],
    #         "key": f["key"],
    #         "energy": f["energy"]
    #     })
    #     t["youtube_url"] = search_youtube(t["title"], t["artist"])
    #     t["soundcloud_url"] = search_soundcloud(t["title"], t["artist"])
    #     track_features.append(t)
    # mix_plan = suggest_transitions(track_features)
    # total_duration = sum([f.get("duration_ms", 180000) for f in audio_features]) // 1000
    # print("\nMix Plan:")
    # for i, track in enumerate(mix_plan):
    #     print(f"{i+1}. {track['title']} - {track['artist']} | BPM: {track['bpm']} | Key: {track['key']} | Energy: {track['energy']:.2f}")
    #     print(f"   YouTube: {track['youtube_url']}")
    #     print(f"   SoundCloud: {track['soundcloud_url']}")
    #     if track['transition_to_next']:
    #         print(f"   Transition: {track['transition_to_next']}")
    # print(f"\nEstimated mix duration: {total_duration//60}:{total_duration%60:02d}")

if __name__ == "__main__":
    main() 