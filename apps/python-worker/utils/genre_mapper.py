"""
Genre Mapper - Maps AI-suggested genres to actual database genres
"""

# Available genres in the database
AVAILABLE_GENRES = [
    "Hip-Hop/Rap",
    "African Music",
    "Reggae",
    "Rap/Hip Hop",
    "R&B",
    "Pop",
    "Dance",
    "Latin Music",
    "Alternative",
    "Films/Games",
    "Rock",
    "Electro",
    "Jazz",
    "Salsa",
    "Bolero",
    "Brazilian Music",
    "Soul & Funk",
    "Reggaeton",
]

# Mapping of common AI suggestions to actual genres
GENRE_MAPPINGS = {
    # Hip Hop variations
    "hip hop": "Hip-Hop/Rap",
    "hip-hop": "Hip-Hop/Rap",
    "rap": "Hip-Hop/Rap",
    "trap": "Hip-Hop/Rap",
    "old school hip hop": "Hip-Hop/Rap",
    # Jazz variations
    "smooth jazz": "Jazz",
    "jazz fusion": "Jazz",
    "nu jazz": "Jazz",
    "acid jazz": "Jazz",
    "lounge": "Jazz",
    "jazz lounge": "Jazz",
    # Electronic variations
    "electronic": "Electro",
    "techno": "Electro",
    "house": "Dance",
    "edm": "Dance",
    "club": "Dance",
    # R&B variations
    "r&b": "R&B",
    "rhythm and blues": "R&B",
    "soul": "Soul & Funk",
    "funk": "Soul & Funk",
    "neo soul": "R&B",
    # Latin variations
    "latin": "Latin Music",
    "salsa": "Salsa",
    "reggaeton": "Reggaeton",
    "bolero": "Bolero",
    # Other
    "reggae": "Reggae",
    "rock": "Rock",
    "alternative": "Alternative",
    "pop": "Pop",
    "brazilian": "Brazilian Music",
    "african": "African Music",
}


def map_genre_to_database(ai_genre: str) -> str:
    """
    Map an AI-suggested genre to an actual database genre.

    Args:
        ai_genre: Genre suggested by AI

    Returns:
        Actual genre from database or None if no mapping found
    """
    # First check if it's already a valid genre
    if ai_genre in AVAILABLE_GENRES:
        return ai_genre

    # Try lowercase mapping
    ai_genre_lower = ai_genre.lower()
    if ai_genre_lower in GENRE_MAPPINGS:
        return GENRE_MAPPINGS[ai_genre_lower]

    # Try partial matches
    for key, value in GENRE_MAPPINGS.items():
        if key in ai_genre_lower or ai_genre_lower in key:
            return value

    # If no mapping found, try to find closest match
    for available in AVAILABLE_GENRES:
        if ai_genre_lower in available.lower() or available.lower() in ai_genre_lower:
            return available

    return None


def get_available_genres() -> list:
    """Get list of available genres in database"""
    return AVAILABLE_GENRES.copy()


def map_multiple_genres(ai_genres: list) -> list:
    """
    Map multiple AI-suggested genres to database genres.

    Args:
        ai_genres: List of genres suggested by AI

    Returns:
        List of mapped database genres (duplicates removed)
    """
    mapped = []
    for genre in ai_genres:
        mapped_genre = map_genre_to_database(genre)
        if mapped_genre and mapped_genre not in mapped:
            mapped.append(mapped_genre)

    # If no genres mapped, return None to avoid empty genre filters
    return mapped if mapped else None
