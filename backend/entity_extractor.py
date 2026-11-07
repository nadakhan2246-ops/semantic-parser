"""Entity extraction using gazetteers + regex (spaCy NER is added if a model is installed).

Everything is returned in the order it appears in the sentence, so "the first location" really is the first one."""
import re

LOCATIONS = ["new york","los angeles","san francisco","new delhi","hyderabad","chennai","mumbai","delhi","bangalore","bengaluru","kolkata","pune","jaipur",
             "ahmedabad","lucknow","kochi","goa","agra","varanasi","madurai","coimbatore","visakhapatnam","vijayawada",
             "india","london","paris","tokyo","dubai","singapore","sydney","berlin","rome","toronto",
             "france","germany","china","japan","italy","spain","russia","brazil","canada","australia","nepal","pakistan","bangladesh","usa","uk"]
OBJECTS = ["weather","temperature","forecast","train","ticket","flight","bus","taxi","cab","hotel","room","information","president",
           "minister","capital","university","universities","population"]
DATE_WORDS = ["day after tomorrow","this weekend","this evening","next week","next month","today","tomorrow","yesterday","tonight",
              "monday","tuesday","wednesday","thursday","friday","saturday","sunday"]   # longer phrases first
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
ROLE_PREPS = {"to": "destination", "from": "origin", "in": "location", "at": "location", "for": "location", "near": "location"}
INFER_PREPS = ("to", "from", "in", "at", "near")   # a Capitalised word after one of these is treated as an unlisted place

# One pattern for all known places; longest names first so "new delhi" wins over "delhi". An optional preposition gives the role.
_LOC_RE = re.compile(r"\b(?:(to|from|in|at|for|near)\s+)?(" + "|".join(re.escape(l) for l in sorted(LOCATIONS, key=len, reverse=True)) + r")\b")

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None

def _is_not_a_place(words):
    return any(w in DATE_WORDS or w in OBJECTS or w[:3] in MONTHS.split("|") for w in words)

def extract_entities(text: str) -> dict:
    low = text.lower()
    ents = {"locations": [], "dates": [], "objects": [], "people": []}

    # --- places from the gazetteer (with role from the preposition before them)
    places, seen = [], set()
    for m in _LOC_RE.finditer(low):
        if m.group(2) in seen: continue
        seen.add(m.group(2))
        places.append((m.start(2), {"text": m.group(2).title(), "role": ROLE_PREPS.get(m.group(1), "location")}))

    # --- Heuristic 1: "to/from/in/at/near" + Capitalised word(s) not in the gazetteer -> an unlisted place (e.g. Nagpur)
    known = {p["text"].lower() for _, p in places}
    inferred = set()
    for m in re.finditer(rf"\b({'|'.join(INFER_PREPS)})\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", text):
        name = m.group(2)
        if _is_not_a_place(name.lower().split()): continue
        if any(k in name.lower() for k in known): continue        # already found through the gazetteer
        if name.lower() in inferred: continue                     # same unlisted place mentioned twice: keep the first
        places.append((m.start(2), {"text": name, "role": ROLE_PREPS[m.group(1)]}))
        inferred.add(name.lower())
    ents["locations"] = [p for _, p in sorted(places, key=lambda x: x[0])]

    # --- dates: longest phrase first, masked with spaces so "day after tomorrow" does not also yield "tomorrow"
    dates, masked = [], low
    for d in DATE_WORDS:
        dates += [(m.start(), d) for m in re.finditer(rf"\b{d}\b", masked)]
        masked = re.sub(rf"\b{d}\b", lambda m: " " * len(m.group(0)), masked)
    for rx in (r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", rf"\b\d{{1,2}}\s*(?:{MONTHS})[a-z]*\b"):
        dates += [(m.start(), m.group(0)) for m in re.finditer(rx, low)]
    ents["dates"] = list(dict.fromkeys(d for _, d in sorted(dates)))

    # --- objects, in sentence order
    objs = [(m.start(), o) for o in OBJECTS for m in [re.search(rf"\b{o}\b", low)] if m]
    ents["objects"] = [o for _, o in sorted(objs)]

    # --- Heuristic 2: remaining capitalised words (not first word, not a known place/date/object) are names
    for m in re.finditer(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", text):
        name, words = m.group(0), m.group(0).lower().split()
        if m.start() == 0 or name.lower() in known or name.lower() in LOCATIONS or name.lower() in inferred: continue
        if _is_not_a_place(words): continue
        if name not in ents["people"]: ents["people"].append(name)

    if _nlp:                                                # optional spaCy NER for people / extra places
        for e in _nlp(text).ents:
            if e.label_ == "PERSON": ents["people"].append(e.text)
            elif e.label_ in ("GPE", "LOC") and e.text.title() not in [l["text"] for l in ents["locations"]]:
                ents["locations"].append({"text": e.text.title(), "role": "location"})
    return ents
