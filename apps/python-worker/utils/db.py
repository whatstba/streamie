import os
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DB", "streamie")

_client = None

def get_db():
    """Return a MongoDB database connection."""
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client[DATABASE_NAME]
