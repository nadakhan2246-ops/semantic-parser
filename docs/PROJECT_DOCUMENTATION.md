# Project Documentation

**AI-Based Natural Language Understanding Using Semantic Parsing**

## 1. Problem and objective
Computers store sentences as plain text; they do not know what a sentence *means*. This project converts an everyday English sentence into a structured, machine-readable meaning (intent, action, object, place, date) using rule-based semantic parsing, and explains every step to the user.

## 2. Architecture
```
Browser (HTML / CSS / JS)  --fetch JSON-->  Flask (app.py)  -->  backend/ NLP modules  -->  SQLite (history)
```
| Layer | Files |
|---|---|
| Web server and API | `app.py`, `config.py` |
| NLP pipeline | `backend/preprocessing.py`, `tokenizer.py`, `parser.py`, `entity_extractor.py`, `intent_classifier.py`, `semantic_analyzer.py`, `response_generator.py` |
| Persistence | `database/database.py`, `backend/history_manager.py` |
| Knowledge | `dataset/intent_patterns.json`, `dataset/sample_sentences.json` |
| Interface | `frontend/index.html`, `style.css`, `script.js`, `assets/logo.svg` |

## 3. The eight pipeline stages
1. **User Input**: the raw sentence is received and validated (non-empty, at most 500 characters).
2. **Text Preprocessing**: whitespace is trimmed, near-miss typos are corrected with `difflib` against the system vocabulary, text is lower-cased and punctuation removed. The original sentence is always kept.
3. **Tokenization**: NLTK's Treebank tokenizer (regex fallback if NLTK is missing).
4. **Semantic Parsing**: the first known action verb is found, the words after it form the object, each prepositional phrase is linked to the object (or to the action if there is no object) as a whole phrase, e.g. `flight --prep_from--> new delhi`, `train ticket --prep_to--> chennai`; the phrase ends at the next preposition, date word or punctuation. A leading question word is detected.
5. **Entity Extraction**: gazetteers and regex find places (with a role: destination, origin or location from the preposition before them), dates (the longest phrase wins, so "day after tomorrow" is not read as "tomorrow"), objects and capitalised names. Everything is returned **in sentence order**, and the longest place name wins ("New Delhi" is not read as "Delhi"). A Capitalised word after `to / from / in / at / near` that is not in the gazetteer is accepted as an unlisted place ("Book a hotel in Nagpur"). Country names are places, not people; a person is only guessed for "who" questions and information searches. spaCy NER is added automatically if installed.
6. **Intent Classification**: each intent owns a list of regex patterns; its score is the fraction that match. Booking intents need every pattern; others need at least 30%. Weak matches become `UNKNOWN`. If two specific intents tie, the one whose cue words appear first in the sentence wins and the other is reported as an ambiguity ("Book a train ticket to Chennai, and show weather" is a booking). The frame's object is chosen to fit the winning intent.
7. **Semantic Interpretation**: the frame is assembled, missing required details (for example no destination) are flagged, and a plain-English meaning is written.
8. **Structured Output**: the JSON frame is returned and saved to history.

Example: `Book a train ticket to Chennai tomorrow.`
```json
{"intent": "BOOK_TRANSPORT", "action": "book", "object": "train ticket", "destination": "Chennai", "date": "tomorrow"}
```

## 4. Unsupported and ambiguous input
* Sentences with no matching intent return `UNKNOWN`; nothing is guessed.
* An action with no supported object ("Book it") is flagged as ambiguous.
* A sentence matching two intents equally ("Book a hotel and a train ticket to Pune") reports the alternatives in its notes.
* Empty, over-long, non-JSON and wrongly-typed requests return a clear JSON error with HTTP 400.

## 5. REST API
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | the web application |
| GET | `/api/health` | liveness check |
| GET | `/api/examples` | example sentences and pipeline stage names |
| POST | `/api/analyze` | body `{"text": "..."}`; returns the full analysis and saves it |
| GET | `/api/history` | latest 50 analyses (newest first) plus `total`, the number of all saved analyses |
| GET | `/api/history/<id>` | one saved analysis |
| DELETE | `/api/history` | delete all history |

Every response contains `"success": true/false`. Errors contain `"error"`. A legacy `"mascot_message"` text field is still returned for backward compatibility; the interface no longer uses it.

If the history database is unavailable, `/api/analyze` still returns the analysis (with `history_id: null` and a `warning`), and the history routes return a JSON `500` error instead of crashing.

## 6. Database
SQLite file `database/history.db` (created automatically on first start) with one table:
`history(id, sentence, intent, result_json, created_at)`. Connections are always closed after use, and saved history persists when the application is restarted (`init_db()` only creates the table if it is missing).

## 7. Limitations and future work
The system is rule-based, so it understands only the vocabulary and patterns it has been given. Future work: a trained intent classifier, dependency parsing with spaCy, a larger gazetteer, and multi-intent sentences.

## 8. Interface (redesign)
The frontend is a single HTML page with five hash-routed views, so every view has its own address and the browser Back button works:

| Route | Purpose |
|---|---|
| `#/home` | Project overview, introduction to semantic parsing, statistics, pipeline overview, Start Analyzing button |
| `#/analyzer` | Input area, quick examples, processing status, eight result sections (original, preprocessed, tokens, semantic parsing, entities, intent, JSON, explanation) |
| `#/pipeline` | The eight stages as a numbered workflow |
| `#/playground` | Example sentence cards; selecting one opens the Analyzer and processes it |
| `#/history` | Table of saved analyses from SQLite with View Analysis and Clear History |

Design tokens: ivory `#FAF7F0`, cream `#FFFDF8`, beige `#E9DDCC`, coffee `#8B6452`, chocolate `#3E2B25`, taupe `#A58B7A`. Fonts: Playfair Display (headings) and Inter (body) from Google Fonts, with Georgia and system fonts as offline fallbacks. The backend, NLP modules and API endpoints were not changed.
