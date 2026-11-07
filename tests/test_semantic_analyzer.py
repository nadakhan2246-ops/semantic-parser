import pytest
from backend.semantic_analyzer import analyze

CASES = [
    ("Hello, how are you?", "GREETING", {}),
    ("Show me the weather in Hyderabad.", "GET_WEATHER", {"location": "Hyderabad", "action": "show"}),
    ("Book a train ticket to Chennai tomorrow.", "BOOK_TRANSPORT", {"destination": "Chennai", "date": "tomorrow", "object": "train ticket"}),
    ("Find information about artificial intelligence.", "SEARCH_INFO", {"object": "artificial intelligence"}),
    ("Who is the president of India?", "GENERAL_QUESTION", {"question_word": "who", "location": "India"}),
    ("I want to book a hotel in Mumbai.", "BOOK_HOTEL", {"location": "Mumbai"}),
]

@pytest.mark.parametrize("text,intent,expected", CASES)
def test_supported(text, intent, expected):
    r = analyze(text)
    assert r["intent"]["intent"] == intent
    for k, v in expected.items():
        assert r["semantic_frame"][k] == v

def test_unsupported_is_unknown():
    r = analyze("asdf qwerty zxcv")
    assert r["intent"]["intent"] == "UNKNOWN" and r["notes"]


def test_spelling_correction():
    r = analyze("Book a trian ticket to Chenai tomorow")
    assert r["semantic_frame"]["destination"] == "Chennai" and r["semantic_frame"]["object"] == "train ticket"
    assert r["corrections"]

def test_person_and_tell_me_about():
    r = analyze("Tell me about Mahatma Gandhi")
    assert r["intent"]["intent"] == "SEARCH_INFO" and r["semantic_frame"]["person"] == "Mahatma Gandhi"

def test_missing_destination_is_flagged():
    r = analyze("Book a train ticket")
    assert r["missing"] == ["destination"]

def test_from_to_flight():
    f = analyze("Can you book me a flight from Pune to Mumbai on Friday")["semantic_frame"]
    assert f["origin"] == "Pune" and f["destination"] == "Mumbai" and f["date"] == "friday"


def test_stages_cover_whole_pipeline():
    r = analyze("Book a train ticket to Chennai tomorrow.")
    assert [s["name"] for s in r["stages"]][0] == "User Input" and r["stages"][-1]["name"] == "Structured Output"
    assert len(r["stages"]) == 8


def test_ambiguous_sentence_is_flagged():
    r = analyze("Book a hotel and a train ticket to Pune")
    assert r["intent"]["alternatives"] and any("Ambiguous" in n for n in r["notes"])


def test_action_without_object_is_ambiguous():
    r = analyze("Book it")
    assert r["intent"]["intent"] == "UNKNOWN" and any("Ambiguous" in n for n in r["notes"])


def test_longest_date_phrase_wins():
    assert analyze("Book a flight to Delhi day after tomorrow")["semantic_frame"]["date"] == "day after tomorrow"


def test_empty_and_symbol_input_do_not_crash():
    for text in ["", "   ", "?!?!", "@@@ ###", "12345"]:
        assert analyze(text)["intent"]["intent"] in {"UNKNOWN", "GENERAL_QUESTION"}


def test_output_is_input_dependent():
    a = analyze("Show me the weather in Delhi")["semantic_frame"]
    b = analyze("Show me the weather in Pune")["semantic_frame"]
    assert a != b and a["location"] == "Delhi" and b["location"] == "Pune"


def test_unsupported_random_sentence():
    assert analyze("The purple elephant danced quietly")["intent"]["intent"] == "UNKNOWN"


# ---- regression tests for problems found while auditing the project ----
def test_everyday_english_word_is_not_spell_corrected():
    r = analyze("Show pairs of shoes")           # "pairs" must not become the city "paris"
    assert r["corrections"] == [] and "location" not in r["semantic_frame"]


def test_country_is_a_location_not_a_person():
    f = analyze("What is the capital of France?")["semantic_frame"]
    assert f["location"] == "France" and "person" not in f


def test_who_question_still_finds_the_person():
    assert analyze("Who is Narendra Modi?")["semantic_frame"]["person"] == "Narendra Modi"


def test_search_topic_does_not_swallow_the_place():
    f = analyze("Search for universities in Pune.")["semantic_frame"]
    assert f["object"] == "universities" and f["location"] == "Pune"


def test_raining_is_a_weather_request():
    r = analyze("Is it raining in Pune?")
    assert r["intent"]["intent"] == "GET_WEATHER" and r["semantic_frame"]["location"] == "Pune"


def test_first_request_wins_in_a_two_intent_sentence():
    r = analyze("Book a train ticket to Chennai tomorrow, and show weather in Chennai")
    assert r["intent"]["intent"] == "BOOK_TRANSPORT" and r["semantic_frame"]["action"] == "book"
    assert any("Ambiguous" in n for n in r["notes"])


@pytest.mark.parametrize("text,key,city", [
    ("Book a hotel in Nagpur", "location", "Nagpur"),
    ("Weather in Nagpur tomorrow", "location", "Nagpur"),
    ("Book a train ticket to Surat", "destination", "Surat"),
])
def test_unlisted_city_is_recognised(text, key, city):
    r = analyze(text)
    assert r["semantic_frame"][key] == city and r["missing"] == []


def test_multiword_city_keeps_its_role():
    f = analyze("Book a flight from New Delhi to Mumbai")["semantic_frame"]
    assert f["origin"] == "New Delhi" and f["destination"] == "Mumbai"


def test_first_location_really_is_the_first_in_the_sentence():
    assert analyze("Weather in Mumbai and Chennai")["semantic_frame"]["location"] == "Mumbai"


def test_object_fits_the_chosen_intent():
    assert analyze("Book a hotel and a train ticket to Pune")["semantic_frame"]["object"] == "hotel"


def test_unsupported_note_names_the_object_when_there_is_one():
    r = analyze("Find hotels near Paris")
    assert r["intent"]["intent"] == "UNKNOWN" and any("'hotel'" in n for n in r["notes"])
    assert not any("no supported object" in n for n in r["notes"])


def test_unlisted_place_mentioned_twice_is_listed_once():
    locs = analyze("Book a flight from New Delhi to Nagpur tomorrow, and show weather in Nagpur")["entities"]["locations"]
    assert [l["text"] for l in locs] == ["New Delhi", "Nagpur"] and locs[1]["role"] == "destination"
