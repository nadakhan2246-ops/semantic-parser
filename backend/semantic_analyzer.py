"""Semantic analyzer: runs the full pipeline and builds the meaning representation."""
from backend.preprocessing import preprocess
from backend.tokenizer import tokenize
from backend.parser import parse
from backend.entity_extractor import extract_entities
from backend.intent_classifier import classify_intent

PIPELINE = ["User Input","Text Preprocessing","Tokenization","Semantic Parsing","Entity Extraction","Intent Classification","Semantic Interpretation","Structured Output"]

INTENT_OBJECTS = {"BOOK_HOTEL": ("hotel", "room"), "GET_WEATHER": ("weather", "temperature", "forecast"),
                  "BOOK_TRANSPORT": ("train", "flight", "bus", "taxi", "cab", "ticket")}

def _first_loc(ents, role):
    return next((l["text"] for l in ents["locations"] if l["role"] == role), None)

def build_frame(intent, parsed, ents):
    """Structured semantic frame (None values are dropped)."""
    wanted = INTENT_OBJECTS.get(intent["intent"], ())          # prefer an object that fits the intent ("hotel" for BOOK_HOTEL)
    obj = next((o for o in ents["objects"] if o in wanted), ents["objects"][0] if ents["objects"] else parsed["object"])
    loc = _first_loc(ents, "location") or _first_loc(ents, "destination")
    if intent["intent"] == "SEARCH_INFO" and parsed.get("topic"): obj = parsed["topic"]
    frame = {"intent": intent["intent"], "action": parsed["action"], "object": obj,
             "location": loc, "destination": _first_loc(ents, "destination") if intent["intent"] == "BOOK_TRANSPORT" else None,
             "origin": _first_loc(ents, "origin"), "date": ents["dates"][0] if ents["dates"] else None,
             "question_word": parsed["question_word"]}
    if intent["intent"] == "BOOK_TRANSPORT":
        frame["location"] = None
        modes = [o for o in ents["objects"] if o in ("train", "flight", "bus", "taxi", "cab")]
        if modes and "ticket" in ents["objects"]: frame["object"] = modes[0] + " ticket"   # compound noun
        elif modes: frame["object"] = modes[0]
    if ents["people"] and (intent["intent"] == "SEARCH_INFO" or (intent["intent"] == "GENERAL_QUESTION" and parsed["question_word"] in ("who", "whom"))):
        frame["person"] = ents["people"][0]
    return {k: v for k, v in frame.items() if v is not None}

def _ticket(f):
    e = f.get('object', 'travel')
    return e if 'ticket' in e else e + ' ticket'

REQUIRED = {'BOOK_TRANSPORT': ['destination'], 'BOOK_HOTEL': ['location'], 'GET_WEATHER': ['location']}

def interpret(intent, frame):
    """Explain the meaning in simple English."""
    i, f = intent["intent"], frame
    where = f" in {f['location']}" if "location" in f else ""
    when = f" for {f['date']}" if "date" in f else ""
    texts = {
        "GREETING": "The user is greeting the assistant and starting a friendly conversation.",
        "GET_WEATHER": f"The user wants the weather{where}{when}.",
        "BOOK_HOTEL": f"The user wants to book a hotel{where}{when}.",
        "BOOK_TRANSPORT": f"The user wants to book a {_ticket(f)}" + (f" from {f['origin']}" if 'origin' in f else "") + (f" to {f['destination']}" if 'destination' in f else "") + when + ".",
        "SEARCH_INFO": f"The user wants to find information about '{f.get('object','the given topic')}'.",
        "GENERAL_QUESTION": f"The user is asking a '{f.get('question_word','general')}' question" + (f" about '{f['object']}'" if 'object' in f else "") + (f" related to {f['location']}" if 'location' in f else "") + ".",
    }
    return texts.get(i, "The sentence does not match any supported intent, so no meaning is guessed.")

def analyze(text: str) -> dict:
    pre = preprocess(text)
    work = pre["corrected"]                       # typo-corrected sentence feeds the rest of the pipeline
    tokens = tokenize(work)
    parsed = parse(tokens)
    ents = extract_entities(work)
    intent = classify_intent(pre["normalized"])
    frame = build_frame(intent, parsed, ents)
    notes = [f"Spelling corrected: '{x['from']}' to '{x['to']}'." for x in pre["fixes"]]
    missing = [s for s in REQUIRED.get(intent["intent"], []) if s not in frame]
    notes += [f"Missing detail: no {s} was mentioned, so the request is incomplete." for s in missing]
    if intent["intent"] == "UNKNOWN":
        notes.append("Unsupported or uncertain input.")
        if parsed["action"] and frame.get("object"):
            notes.append(f"Unsupported request: the action '{parsed['action']}' on '{frame['object']}' does not match any supported intent.")
        elif parsed["action"]:
            notes.append(f"Ambiguous request: the action '{parsed['action']}' was found, but no supported object (such as a hotel or ticket) was mentioned.")
    if intent["alternatives"]:
        notes.append("Ambiguous sentence: it also matches " + ", ".join(intent["alternatives"]) + "; " + intent["intent"] + " was chosen.")
    if len(ents["locations"]) > 1 and intent["intent"] != "BOOK_TRANSPORT": notes.append("Multiple locations found; the first was used.")
    n_ents = len(ents["locations"]) + len(ents["dates"]) + len(ents["objects"]) + len(ents["people"])
    stages = [
        {"name": "User Input", "detail": f"{len(pre['original'])} characters received"},
        {"name": "Text Preprocessing", "detail": f"lower-cased, punctuation removed, {len(pre['fixes'])} spelling fix(es)"},
        {"name": "Tokenization", "detail": f"{len(tokens)} tokens"},
        {"name": "Semantic Parsing", "detail": f"action: {parsed['action'] or 'none'}, {len(parsed['relations'])} relation(s)"},
        {"name": "Entity Extraction", "detail": f"{n_ents} entit{'y' if n_ents == 1 else 'ies'} found"},
        {"name": "Intent Classification", "detail": f"{intent['intent']} ({round(intent['confidence'] * 100)}%)"},
        {"name": "Semantic Interpretation", "detail": "meaning frame built" + (f", {len(missing)} detail(s) missing" if missing else "")},
        {"name": "Structured Output", "detail": f"{len(frame)} JSON field(s)"},
    ]
    return {"original": pre["original"], "preprocessed": pre["normalized"], "tokens": tokens, "parse": parsed,
            "entities": ents, "intent": intent, "interpretation": interpret(intent, frame),
            "semantic_frame": frame, "missing": missing, "corrections": pre["fixes"], "notes": notes, "stages": stages}
