"""Thin layer between the Flask routes and the database."""
from database import database as db

def save_analysis(result):  return db.insert(result["original"], result["intent"]["intent"], result)
def list_history():         return db.fetch_all()
def count_history():        return db.count()
def get_entry(entry_id):    return db.fetch_one(entry_id)
def clear_history():        db.clear()
