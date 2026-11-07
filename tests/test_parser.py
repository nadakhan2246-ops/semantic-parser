from backend.tokenizer import tokenize
from backend.parser import parse
from backend.preprocessing import preprocess

def test_preprocess_keeps_original():
    r = preprocess("  Show   me THE weather!  ")
    assert r["original"] == "  Show   me THE weather!  " and r["normalized"] == "show me the weather"

def test_tokenize():
    assert tokenize("Hello, how are you?")[:2] == ["Hello", ","]

def test_action_and_object():
    p = parse(tokenize("Show me the weather in Hyderabad."))
    assert p["action"] == "show" and p["object"] == "weather"

def test_want_to_book():
    assert parse(tokenize("I want to book a hotel in Mumbai."))["action"] == "book"

def test_question_word():
    assert parse(tokenize("Who is the president of India?"))["question_word"] == "who"

def test_topic():
    assert parse(tokenize("Find information about artificial intelligence."))["topic"] == "artificial intelligence"


def test_topic_stops_at_the_next_preposition():
    assert parse(tokenize("Find information on machine learning in India"))["topic"] == "machine learning"


def _rels(sentence):
    return {(r["head"], r["relation"], r["dependent"]) for r in parse(tokenize(sentence))["relations"]}


def test_relations_attach_to_the_object_and_keep_multiword_places_together():
    rels = _rels("Book a flight from New Delhi to Nagpur tomorrow")
    assert ("flight", "prep_from", "new delhi") in rels and ("flight", "prep_to", "nagpur") in rels


def test_relations_for_simple_sentence():
    assert _rels("Show me the weather in Hyderabad.") >= {("show", "action_on", "weather"), ("weather", "prep_in", "hyderabad")}
