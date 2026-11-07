"""Rule-based semantic parser: finds the action (verb), object and grammatical relations."""
from backend.tokenizer import STOPWORDS
from backend.entity_extractor import DATE_WORDS
VERBS = {"show","find","search","book","reserve","get","tell","give","display","check","look"}
WANT_WORDS = {"want","need","like","wish"}
PREPS = {"to","in","at","from","for","about","on"}
QUESTION_WORDS = {"who","what","when","where","why","which","how"}
DATE_STARTS = {d.split()[0] for d in DATE_WORDS}              # first word of every date phrase ("next", "day", "tomorrow", ...)

def _phrase_after(low: list, k: int):
    """Words after the preposition at index k, up to the next preposition, date word or punctuation ("new delhi")."""
    out = []
    for w in low[k + 1:]:
        if w in PREPS or w in DATE_STARTS or not w.isalnum(): break
        if w in STOPWORDS:
            if out: break                                     # "the" at the start is skipped; a stopword after the phrase ends it
            continue
        out.append(w)
    return " ".join(out) or None

def parse(tokens: list) -> dict:
    low = [t.lower() for t in tokens]
    action = next((t for t in low if t in VERBS), None)     # first known action verb
    subject = "user" if ("i" in low or action) else None     # imperative sentences imply the user
    obj, relations = None, []
    if action:
        i = low.index(action)
        chunk = []
        for t in low[i + 1:]:
            if t in PREPS and chunk: break                   # stop at the first preposition after the object
            if t.isalnum() and t not in STOPWORDS: chunk.append(t)
        obj = " ".join(chunk) or None
        relations.append({"head": action, "relation": "action_on", "dependent": obj})
    for k, t in enumerate(low):                              # prepositional relations
        if t in PREPS and k + 1 < len(low):
            dep = _phrase_after(low, k)
            head = obj or action or (low[k - 1] if k else None)   # a prepositional phrase modifies the object (else the action)
            if dep: relations.append({"head": head, "relation": f"prep_{t}", "dependent": dep})
    topic = None                                             # words after "about/on/for" form the topic
    for k, t in enumerate(low):
        if t in {"about", "on", "for"}:
            words = []
            for w in low[k + 1:]:
                if w in PREPS and words: break                    # "universities in pune" -> topic is just "universities"
                if w.isalnum() and w not in STOPWORDS: words.append(w)
            if words: topic = " ".join(words); break
    qword = next((t for t in low if t in QUESTION_WORDS), None) if low and low[0] in QUESTION_WORDS else None
    return {"action": action, "subject": subject, "object": obj, "question_word": qword, "topic": topic,
            "wants": any(t in WANT_WORDS for t in low), "relations": relations}
