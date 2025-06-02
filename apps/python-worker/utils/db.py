import os
from urllib.parse import quote_plus
from pymongo import MongoClient

MONGODB_PASSWORD = os.getenv("MONGO_DB_PW", "")
MONGODB_URI = f"mongodb+srv://lyn:{MONGODB_PASSWORD}@dev.5umbita.mongodb.net/?retryWrites=true&w=majority&appName=Dev"

DATABASE_NAME = os.getenv("MONGODB_DB", "streamie")

_client = None

def get_db():
    """Return a MongoDB database connection."""
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client[DATABASE_NAME]
