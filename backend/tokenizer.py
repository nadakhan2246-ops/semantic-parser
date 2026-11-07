"""Tokenization: uses NLTK if installed, otherwise a regex fallback."""
import re
try:
    from nltk.tokenize import TreebankWordTokenizer
    _tk = TreebankWordTokenizer()          # rule-based, needs no data download
except Exception:
    _tk = None

STOPWORDS = {"a","an","the","me","my","i","is","are","of","to","in","at","for","on","please","about","some","you","it","and"}

def tokenize(text: str) -> list:
    tokens = _tk.tokenize(text) if _tk else re.findall(r"\w+|[^\w\s]", text)
    return [t for t in tokens if t.strip()]
