# intent_detection.py
# ---------------------------------------------------------------------------
# Two-stage pipeline:
#   Stage 1 — Keyword check: does input mention a known scheme? (instant)
#             If yes → return specific_scheme immediately, skip LLM
#   Stage 2 — LLM: extract eligibility fields from personal info
# ---------------------------------------------------------------------------

import json
import os
from ollama import chat
from json_parser import parse_llm_json, _fallback


# ---------------------------------------------------------------------------
# Load schemes for keyword matching
# ---------------------------------------------------------------------------

_SCHEMES_PATH = os.path.join(os.path.dirname(__file__), "schemes.json")

def _load_schemes():
    with open(_SCHEMES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

SCHEMES = _load_schemes()

# Build a flat lookup: every alias/id → scheme id
# e.g. "pmay" → "pmay", "awas yojana" → "pmay", "आवास योजना" → "pmay"
ALIAS_MAP = {}
for scheme in SCHEMES:
    sid = scheme["id"]
    ALIAS_MAP[sid.lower()] = sid
    for alias in scheme.get("aliases", []):
        ALIAS_MAP[alias.lower()] = sid

# Trigger phrases that indicate a specific scheme question
SCHEME_QUESTION_TRIGGERS = [
    "के बारे में", "kya hai", "क्या है", "बताओ", "बताइए", "जानना",
    "tell me about", "what is", "details", "info", "explain",
    "जानकारी", "समझाओ", "बताएं", "क्या होती है", "कैसे मिलेगा",
    "के लिए कैसे", "में कैसे", "कैसे करें", "समझाइए"
]

# ---------------------------------------------------------------------------
# Stage 1 — Keyword scheme detector (no LLM)
# ---------------------------------------------------------------------------

def _detect_specific_scheme(text: str) -> dict | None:
    """
    Checks if user input mentions a known scheme name/alias AND
    a question trigger word. If yes, returns specific_scheme response
    immediately without calling the LLM.
    """
    text_lower = text.lower().strip()

    # Check if any trigger word is present
    has_trigger = any(t in text_lower for t in SCHEME_QUESTION_TRIGGERS)
    if not has_trigger:
        return None

    # Check if any scheme alias is present
    matched_id = None
    matched_len = 0
    for alias, sid in ALIAS_MAP.items():
        if alias in text_lower and len(alias) > matched_len:
            matched_id = sid
            matched_len = len(alias)  # prefer longest match

    if not matched_id:
        return None

    # Found a specific scheme query — return without calling LLM
    return {
        "intent": "specific_scheme",
        "specific_scheme_id": matched_id,
        "extracted": {
            "age": None, "gender": None, "caste": None,
            "max_income_annual": None, "farmer": None, "marital_status": None
        },
        "missing_fields": [],
        "follow_up_question_hi": "",
        "unrelated_response_hi": ""
    }


# ---------------------------------------------------------------------------
# Stage 2 — LLM for eligibility field extraction
# ---------------------------------------------------------------------------

# OLD CODE - uses system prompt (doesn't work with welfare-agent-ft):
# _PROMPT_PATH = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
# def _load_system_prompt() -> str:
#     try:
#         with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
#             return f.read().strip()
#     except FileNotFoundError:
#         return ""
# SYSTEM_PROMPT = _load_system_prompt()

# NEW CODE - NO system prompt (matches fine-tuned model training format!)
# The welfare-agent-ft model was trained WITHOUT a system prompt.
# Format: <|begin_of_text|><|start_header_id|>user<|end_header_id|>{input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>


def detect_intent(hindi_text: str) -> dict:
    """
    Main entry point.
    1. Try keyword scheme detection first (instant, no LLM)
    2. Fall back to LLM for eligibility extraction
    """
    if not hindi_text or not hindi_text.strip():
        return _fallback("empty input")

    # Stage 1 — keyword check
    scheme_result = _detect_specific_scheme(hindi_text)
    if scheme_result:
        print(f"[*] Scheme detected by keyword: {scheme_result['specific_scheme_id']}")
        return scheme_result

    # Stage 2 — LLM (NO system prompt - matches training format!)
    try:
        # Use the exact format the model was trained on
        response = chat(
            model="welfare-agent-ft:latest",
            messages=[
                {"role": "user", "content": hindi_text}
            ],
            options={
                "temperature": 0.0,
                "num_predict": 300,
            }
        )
        raw = response.message.content.strip()
        print(f"[LLM] Raw output: {raw}")
        return parse_llm_json(raw)

    except Exception as e:
        print(f"[!] Ollama error: {e}")
        return _fallback(str(e))


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        "मैं पीएमएवाई के बारे में जानना चाहता हूँ",   # specific scheme (keyword)
        "pmjay के बारे में बताओ",                       # specific scheme (keyword)
        "KCC kya hai",                                  # specific scheme (keyword)
        "मैं 65 साल का SC किसान हूं",                  # eligibility → LLM
        "आज मौसम कैसा है?",                            # unrelated → LLM
    ]
    for text in tests:
        print(f"\n[INPUT] {text}")
        result = detect_intent(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
