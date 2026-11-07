"""Central configuration for the project."""
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "history.db")
PATTERNS_PATH = os.path.join(BASE_DIR, "dataset", "intent_patterns.json")
SAMPLES_PATH = os.path.join(BASE_DIR, "dataset", "sample_sentences.json")
MAX_INPUT_LENGTH = 500
CONFIDENCE_THRESHOLD = 0.3   # below this the intent is reported as UNKNOWN
