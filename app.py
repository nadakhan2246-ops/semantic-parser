"""Flask entry point: serves the frontend and exposes the JSON API."""
import json
import sqlite3
import logging
from flask import Flask, request, jsonify, send_from_directory
from config import BASE_DIR, SAMPLES_PATH, MAX_INPUT_LENGTH
from backend.semantic_analyzer import analyze, PIPELINE
from backend.response_generator import build_response, build_error
from backend import history_manager as history
from database.database import init_db
import os

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "frontend"), static_url_path="/static")
app.json.sort_keys = False            # keep the JSON field order intent, action, object, ...
try:
    init_db()
except sqlite3.Error:                 # the app still starts; history routes then report a clear database error
    logging.getLogger(__name__).exception("Could not initialise the history database")

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/api/health")
def health():
    return jsonify({"success": True, "status": "ok"})

@app.get("/api/examples")
def examples():
    with open(SAMPLES_PATH, encoding="utf-8") as f:
        return jsonify({"success": True, "examples": json.load(f), "pipeline": PIPELINE})

@app.post("/api/analyze")
def analyze_route():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):                            # missing body, invalid JSON, or a list/string
        return build_error("Invalid request: send JSON like {\"text\": \"your sentence\"}.")
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        return build_error("Please enter a sentence to analyze.")
    if len(text) > MAX_INPUT_LENGTH:
        return build_error(f"Sentence is too long (maximum {MAX_INPUT_LENGTH} characters).")
    try:
        result = analyze(text)
    except Exception as exc:                                  # never crash the server on odd input
        app.logger.exception("Analysis failed")
        return build_error(f"Analysis failed: {exc}", 500)
    try:
        history_id, warning = history.save_analysis(result), None
    except sqlite3.Error:                                     # a good analysis must not be lost because history is unavailable
        app.logger.exception("Could not save history")
        history_id, warning = None, "The analysis succeeded but could not be saved to history."
    response = build_response(result, history_id)
    if warning: response["warning"] = warning
    return jsonify(response)

@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return build_error("Endpoint not found.", 404)
    return send_from_directory(app.static_folder, "index.html")

@app.errorhandler(405)
def bad_method(_e):
    return build_error("Method not allowed for this endpoint.", 405)

@app.errorhandler(500)
def server_error(_e):
    return build_error("Unexpected server error.", 500)

def _db_error(_exc):
    app.logger.exception("Database error")
    return build_error("Database error: history is currently unavailable.", 500)

@app.get("/api/history")
def history_list():
    try:
        return jsonify({"success": True, "history": history.list_history(), "total": history.count_history()})
    except sqlite3.Error as exc:
        return _db_error(exc)

@app.get("/api/history/<int:entry_id>")
def history_get(entry_id):
    try:
        entry = history.get_entry(entry_id)
    except sqlite3.Error as exc:
        return _db_error(exc)
    if entry is None:
        return build_error("History entry not found.", 404)
    return jsonify(build_response(entry["result"], entry_id))

@app.delete("/api/history")
def history_clear():
    try:
        history.clear_history()
    except sqlite3.Error as exc:
        return _db_error(exc)
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
