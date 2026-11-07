"""Quick end-to-end check of the NLP pipeline. Prints every result and exits with code 1 if any expectation fails."""
import json, sys
from backend.semantic_analyzer import analyze

CASES = [
    ("Hello, how are you?", "GREETING"),
    ("Show me the weather in Hyderabad.", "GET_WEATHER"),
    ("Book a train ticket to Chennai tomorrow.", "BOOK_TRANSPORT"),
    ("Find information about artificial intelligence.", "SEARCH_INFO"),
    ("Who is the president of India?", "GENERAL_QUESTION"),
    ("I want to book a hotel in Mumbai.", "BOOK_HOTEL"),
    ("asdf qwerty zxcv", "UNKNOWN"),
]
failed = 0
for sentence, expected in CASES:
    r = analyze(sentence)
    got = r["intent"]["intent"]
    ok = got == expected
    failed += not ok
    print(("OK   " if ok else "FAIL ") + sentence, "->", got, json.dumps(r["semantic_frame"]))
    print("     ", r["interpretation"])
print(f"\n{len(CASES) - failed}/{len(CASES)} smoke checks passed")
sys.exit(1 if failed else 0)
