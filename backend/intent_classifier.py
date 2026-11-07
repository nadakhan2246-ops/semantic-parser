"""Rule-based intent classification: score = fraction of an intent's patterns that match."""
import json, re
from config import PATTERNS_PATH, CONFIDENCE_THRESHOLD

with open(PATTERNS_PATH, encoding="utf-8") as f:
    INTENTS = json.load(f)

def _completed_at(patterns, text):
    """Position where an intent's last cue word appears (earlier = that request is stated first)."""
    starts = [m.start() for m in (re.search(p, text) for p in patterns) if m]
    return max(starts) if starts else len(text)

def classify_intent(normalized: str) -> dict:
    scores = {}
    for name, info in INTENTS.items():
        hits = sum(1 for p in info["patterns"] if re.search(p, normalized))
        scores[name] = hits / len(info["patterns"])
    # Best score wins; GENERAL_QUESTION loses ties to a specific intent; if two specific intents tie,
    # the one whose cue words appear first in the sentence wins ("Book a train ..., and show weather" -> booking).
    best = max(scores, key=lambda k: (scores[k], k != "GENERAL_QUESTION", -_completed_at(INTENTS[k]["patterns"], normalized)))
    conf = scores[best]
    # other specific intents that scored exactly as high -> the sentence is ambiguous
    alternatives = [k for k, v in scores.items() if k != best and v == conf and conf > 0 and k != "GENERAL_QUESTION"]
    rounded = {k: round(v, 2) for k, v in scores.items()}
    # booking intents need ALL patterns; other intents need at least CONFIDENCE_THRESHOLD
    if conf < CONFIDENCE_THRESHOLD or (best.startswith("BOOK") and conf < 1):
        return {"intent": "UNKNOWN", "confidence": round(conf, 2), "description": "unsupported or unclear request",
                "scores": rounded, "alternatives": []}
    return {"intent": best, "confidence": round(conf, 2), "description": INTENTS[best]["description"],
            "scores": rounded, "alternatives": alternatives}
