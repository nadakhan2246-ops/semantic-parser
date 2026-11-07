# AI-Based Natural Language Understanding Using Semantic Parsing

An academic NLP web application. Type an English sentence; the app finds its **intent**, **entities** and **structure** and returns a JSON meaning that a program can use. Professional brown-and-beige interface with five views: Home, Analyzer, Pipeline, Playground and History.

## Features
Landing page with project overview, sentence analyzer dashboard, live 8-stage pipeline view, tokens, entity extraction (places with roles, dates, objects, names), semantic parse tree and relations, intent classification with confidence and per-intent scores, plain-English interpretation, structured JSON with **Copy JSON**, example playground, SQLite analysis history (view and clear), spelling correction (everyday English words are protected), unlisted-city recognition, ambiguity and missing-detail warnings, responsive layout with mobile menu.

## Folder structure
    app.py                    Flask server and API routes
    config.py                 paths and settings
    backend/                  preprocessing, tokenizer, parser, entity_extractor, intent_classifier,
                              semantic_analyzer, response_generator, history_manager
    database/database.py      SQLite helpers (history.db is created on first run)
    dataset/                  intent_patterns.json, sample_sentences.json
    frontend/                 index.html, style.css, script.js, assets/logo.svg
    tests/                    test_parser.py, test_semantic_analyzer.py, test_api.py
    docs/                     PROJECT_DOCUMENTATION.md, TEST_REPORT.md
    smoke_test.py             quick end-to-end check
    requirements.txt          Flask, NLTK, pytest
    requirements-optional.txt spaCy (optional extra entity recognition)

## Install and run (Windows PowerShell)
    cd Semantic_Parsing_Project
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python app.py
Open **http://127.0.0.1:5000** in your browser. Stop the server with `Ctrl+C`.

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` first.
Optional spaCy support: `pip install -r requirements-optional.txt` then `python -m spacy download en_core_web_sm`.
To use another port: `$env:PORT=5001; python app.py`.

## Run the tests
    python -m pytest -v
    python smoke_test.py

## Sample inputs and outputs
| Input | Output |
|---|---|
| Show me the weather in Hyderabad. | `{"intent":"GET_WEATHER","action":"show","object":"weather","location":"Hyderabad"}` |
| Book a train ticket to Chennai tomorrow. | `{"intent":"BOOK_TRANSPORT","action":"book","object":"train ticket","destination":"Chennai","date":"tomorrow"}` |
| I want to book a hotel in Mumbai. | `{"intent":"BOOK_HOTEL","action":"book","object":"hotel","location":"Mumbai"}` |
| Who is the president of India? | `{"intent":"GENERAL_QUESTION","object":"president","location":"India","question_word":"who"}` |
| asdf qwerty zxcv | `{"intent":"UNKNOWN"}` (no meaning is guessed) |

## Extending
Add cities, objects and dates in `backend/entity_extractor.py`, verbs in `backend/parser.py`, and intents in `dataset/intent_patterns.json`.

See `docs/PROJECT_DOCUMENTATION.md` for the architecture, pipeline and API reference.
