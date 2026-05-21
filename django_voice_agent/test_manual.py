# test_manual.py — manual text input to test pipeline without STT
# Run: python test_manual.py

import json
from intent_detection import detect_intent
from eligibility_engine import SchemeEngine

engine = SchemeEngine("schemes.json")

UNRELATED_MSG    = "माफ़ करें, मैं केवल सरकारी योजनाओं के बारे में जानकारी दे सकता हूं।"
PARSE_ERROR_MSG  = "माफ़ करें, मुझे समझ नहीं आया। क्या आप दोबारा बोल सकते हैं?"

def fresh_profile() -> dict:
    return {"age":None,"gender":None,"caste":None,
            "max_income_annual":None,"farmer":None,"marital_status":None}

current_profile = fresh_profile()

def reset_profile():
    global current_profile
    current_profile = fresh_profile()
    print("🔄 नया सत्र शुरू।")

def merge_profile(new: dict):
    for field, value in new.items():
        if field in current_profile and value is not None:
            current_profile[field] = value

def speak(text: str):
    print(f"\n🔊 [AGENT]: {text}\n")

def format_eligible_names(schemes: list) -> str:
    if not schemes:
        return "अभी तक कोई पक्की योजना नहीं मिली।"
    names = ", ".join(f"{i+1}. {s['name']}" for i, s in enumerate(schemes))
    return f"आपके लिए {len(schemes)} योजनाएं मिली हैं: {names}।"

def format_scheme_detail(scheme: dict) -> str:
    return (f"{scheme['name']}। विवरण: {scheme['description']} "
            f"फ़ायदा: {scheme['benefits']} "
            f"आवेदन: {scheme['how_to_apply']} "
            f"हेल्पलाइन: {scheme['helpline']}।")

def handle(llm_json: dict):
    intent = llm_json.get("intent", "incomplete")

    if "_error" in llm_json:
        speak(PARSE_ERROR_MSG)
        return

    if intent == "unrelated":
        speak(UNRELATED_MSG)
        return

    if intent == "specific_scheme":
        sid    = llm_json.get("specific_scheme_id")
        scheme = engine.find_scheme(sid) if sid else None
        speak(format_scheme_detail(scheme) if scheme
              else "माफ़ करें, यह योजना हमारी सूची में नहीं है।")
        return

    # scheme_query / incomplete — update profile
    merge_profile(engine.profile_from_llm_json(llm_json))

    result   = engine.evaluate_all(current_profile)
    eligible = result["eligible"]
    pending  = result["pending"]

    print(f"🧑 Profile : {current_profile}")
    print(f"✅ Eligible: {[s['name'] for s in eligible]}")
    print(f"⏳ Pending : {[(s['name'], s['skipped_fields']) for s in pending]}")

    speak(format_eligible_names(eligible))

    # Use ENGINE's hardcoded follow-up question — not model's
    if pending:
        first    = pending[0]
        question = engine._followup_question(first["skipped_fields"][0])
        speak(f"कुछ और योजनाएं हो सकती हैं। {first['name']} के लिए — {question}")
    elif intent == "incomplete":
        missing  = engine.get_missing_fields(current_profile)
        if missing:
            speak(engine._followup_question(missing[0]))

if __name__ == "__main__":
    print("─"*55)
    print("  MANUAL PIPELINE TEST | 'reset' = नया व्यक्ति | 'quit' = बाहर")
    print("─"*55)
    speak("नमस्ते! कृपया अपनी जानकारी बताइए।")
    while True:
        try:
            user_input = input("📥 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input: continue
        if user_input.lower() == "quit":
            speak("धन्यवाद! नमस्ते।"); break
        if user_input.lower() == "reset":
            reset_profile(); speak("नमस्ते! कृपया नई जानकारी बताइए।"); continue
        llm_json = detect_intent(user_input)
        print(f"\n📊 LLM: {json.dumps(llm_json, ensure_ascii=False)}")
        handle(llm_json)
