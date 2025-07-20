from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Deprecated
def interpret_mood(prompt):
    # Simple hardcoded mapping for MVP
    mapping = {
        "afrobeats party starter": {
            "genre": "afrobeats",
            "bpm_min": 100,
            "bpm_max": 120,
            "energy": 0.7,
        },
        "deep house afterhours": {
            "genre": "deep house",
            "bpm_min": 118,
            "bpm_max": 124,
            "energy": 0.5,
        },
        "nostalgic r&b": {"genre": "r&b", "bpm_min": 70, "bpm_max": 90, "energy": 0.4},
    }
    if prompt.lower() in mapping:
        return mapping[prompt.lower()]
    # Optional: Use OpenAI for more flexible prompts
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a music expert."},
            {
                "role": "user",
                "content": f"Given the mood '{prompt}', suggest a genre, BPM range, and energy (0-1).",
            },
        ],
        max_tokens=50,
        temperature=0.5,
    )
    # Parse response (very basic)
    return {"genre": "pop", "bpm_min": 100, "bpm_max": 120, "energy": 0.6}
