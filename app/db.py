"""MongoDB connection shared by the API."""
import os

from bson import ObjectId
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://demo:demo@localhost:27017/")

client = MongoClient(MONGO_URL)
db = client["shop"]  # databases and collections are created lazily on first write


def clean(doc):
    """Make a document JSON-friendly: ObjectId -> str (recursively)."""
    if isinstance(doc, list):
        return [clean(d) for d in doc]
    if isinstance(doc, dict):
        return {k: clean(v) for k, v in doc.items()}
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc
