"""Text preprocessing: keep the original, correct simple typos, clean and normalise."""
import re, difflib
from backend.entity_extractor import LOCATIONS, OBJECTS, DATE_WORDS
from backend.parser import VERBS, QUESTION_WORDS

# Words the system knows; typos are matched against this vocabulary.
VOCAB = {w for p in LOCATIONS + OBJECTS + DATE_WORDS for w in p.split()} | VERBS | QUESTION_WORDS | {"hello", "information", "tomorrow", "weather"}
# Common English words that must never be "corrected".
COMMON = set("there these those this that then them they with have will would could should tell give need want like what when which your from some about into here where whole going rain pair pairs bush motel tick much such each very more most many".split())

def correct_spelling(text: str):
    """Replace near-miss words (e.g. 'trian' -> 'train') using difflib. Returns (text, fixes)."""
    fixes = []
    def fix(m):
        w, lw = m.group(0), m.group(0).lower()
        if len(lw) < 4 or lw in VOCAB or lw in COMMON:
            return w
        close = difflib.get_close_matches(lw, VOCAB, n=1, cutoff=0.8)
        if not close:
            return w
        fixes.append({"from": w, "to": close[0]})
        return close[0].title() if w[0].isupper() else close[0]
    return re.sub(r"[A-Za-z]+", fix, text), fixes

def preprocess(text: str) -> dict:
    original = text
    cleaned = re.sub(r"\s+", " ", text).strip()              # remove extra whitespace
    corrected, fixes = correct_spelling(cleaned)               # fix simple typos
    normalized = corrected.lower()                             # lowercase for matching
    normalized = re.sub(r"[^\w\s?'/-]", " ", normalized)       # drop punctuation except ? ' / -
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return {"original": original, "cleaned": cleaned, "corrected": corrected, "fixes": fixes, "normalized": normalized}
