def suggest_transitions(track_features):
    mix_plan = []
    for i, track in enumerate(track_features):
        transition = None
        if i < len(track_features) - 1:
            next_track = track_features[i + 1]
            # Simple BPM/key compatibility check
            bpm_diff = abs(track["tempo"] - next_track["tempo"])
            key_match = track["key"] == next_track["key"]
            if bpm_diff <= 4 and key_match:
                transition = {"type": "tempo match", "cue_point": "end"}
            elif bpm_diff <= 8:
                transition = {"type": "echo out", "cue_point": "end"}
            else:
                transition = {"type": "EQ cut", "cue_point": "end"}
        mix_plan.append(
            {
                "title": track["title"],
                "artist": track["artist"],
                "bpm": track["tempo"],
                "key": track["key"],
                "energy": track["energy"],
                "youtube_url": track.get("youtube_url"),
                "soundcloud_url": track.get("soundcloud_url"),
                "transition_to_next": transition,
            }
        )
    return mix_plan
