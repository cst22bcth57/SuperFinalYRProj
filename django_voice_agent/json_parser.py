# json_parser.py
# Simplified — model no longer outputs follow_up_question_hi or unrelated_response_hi
# Those are handled by eligibility_engine hardcoded questions

import json, re

VALID_INTENTS = {"scheme_query", "incomplete", "unrelated", "specific_scheme"}
INTENT_MAP    = {
    "complete":        "scheme_query",
    "scheme_query":    "scheme_query",
    "incomplete":      "incomplete",
    "unrelated":       "unrelated",
    "specific_scheme": "specific_scheme",
}

def parse_llm_json(raw: str) -> dict:
    if not raw or not raw.strip():
        return _fallback("empty response")
    cleaned = _clean(raw)
    for block in _extract_all_blocks(cleaned):
        result = _try_parse(block)
        if result and "intent" in result and "extracted" in result:
            return _normalize(result)
    result = _try_parse(cleaned)
    if result and "intent" in result:
        return _normalize(result)
    print(f"⚠️  JSON parse failed. Raw:\n{raw[:200]}")
    return _fallback("json parse error")

def _clean(raw: str) -> str:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    raw = re.sub(r",\s*null\s*,", ",", raw)
    raw = re.sub(r",\s*null\s*}", "}", raw)
    raw = re.sub(r"{\s*null\s*,", "{", raw)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return raw

def _extract_all_blocks(text: str) -> list:
    blocks, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(text[start:i+1])
                start = None
    return blocks

def _try_parse(text: str) -> dict | None:
    if not text: return None
    try: return json.loads(text)
    except json.JSONDecodeError: return None

def _normalize(data: dict) -> dict:
    # Fix intent
    data["intent"] = INTENT_MAP.get(data.get("intent", "incomplete"), "incomplete")

    # Strip to only 6 valid fields — ignore anything model invents
    raw = data.get("extracted", {})
    ext = {
        "age":               raw.get("age"),
        "gender":            raw.get("gender"),
        "caste":             raw.get("caste"),
        "max_income_annual": raw.get("max_income_annual"),
        "farmer":            raw.get("farmer"),
        "marital_status":    raw.get("marital_status"),
    }
    data["extracted"]          = ext
    data["missing_fields"]     = [k for k, v in ext.items() if v is None]
    data["specific_scheme_id"] = data.get("specific_scheme_id")

    # Remove follow_up and unrelated fields if model still outputs them
    data.pop("follow_up_question_hi", None)
    data.pop("unrelated_response_hi", None)
    return data

def _fallback(reason: str) -> dict:
    return {
        "intent":             "incomplete",
        "specific_scheme_id": None,
        "extracted": {
            "age": None, "gender": None, "caste": None,
            "max_income_annual": None, "farmer": None, "marital_status": None,
        },
        "missing_fields": ["age","gender","caste","max_income_annual","farmer","marital_status"],
        "_error": reason,
    }
