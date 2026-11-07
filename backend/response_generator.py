"""Builds the final API response and the mascot's message."""
MASCOT = {
    "GREETING": "Hello there! Nice to meet you!",
    "UNKNOWN": "Hmm, I'm not sure about that one. Let's try another sentence!",
    "GET_WEATHER": "Your results are ready! Looks like a weather request.",
    "BOOK_HOTEL": "Your results are ready! A hotel booking, I see.",
    "BOOK_TRANSPORT": "Your results are ready! A travel booking, I see.",
    "SEARCH_INFO": "Your results are ready! You're looking for information.",
    "GENERAL_QUESTION": "Your results are ready! That's a question.",
}

def build_response(result: dict, history_id=None) -> dict:
    msg = MASCOT.get(result["intent"]["intent"], "Your results are ready!")
    return {"success": True, "mascot_message": msg, "history_id": history_id, "result": result}

def build_error(message: str, status: int = 400) -> tuple:
    return {"success": False, "error": message, "mascot_message": "Oops! Please check your input."}, status
