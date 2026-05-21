import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from intent_detection import detect_intent
from eligibility_engine import SchemeEngine

engine = SchemeEngine("schemes.json")

UNRELATED_MSG = "माफ़ करें, मैं केवल सरकारी योजनाओं के बारे में जानकारी दे सकता हूं।"
PARSE_ERROR_MSG = "माफ़ करें, मुझे समझ नहीं आया। क्या आप दोबारा बोल सकते हैं?"


def fresh_profile():
    return {
        "age": None,
        "gender": None,
        "caste": None,
        "max_income_annual": None,
        "farmer": None,
        "marital_status": None,
    }


def merge_profile(current_profile, new):
    for field, value in new.items():
        if field in current_profile and value is not None:
            current_profile[field] = value


def format_eligible_names(schemes):
    if not schemes:
        return "अभी तक कोई पक्की योजना नहीं मिली।"
    names = ", ".join(f"{i+1}. {s['name']}" for i, s in enumerate(schemes))
    return f"आपके लिए {len(schemes)} योजनाएं मिली हैं: {names}।"


def format_scheme_detail(scheme):
    return (
        f"{scheme['name']}। "
        f"विवरण: {scheme['description']} "
        f"फ़ायदा: {scheme['benefits']} "
        f"आवेदन: {scheme['how_to_apply']} "
        f"हेल्पलाइन: {scheme['helpline']}।"
    )


def home(request):
    return render(request, "index.html")


@csrf_exempt
def reset_session(request):
    """Clear the user's eligibility profile so a new conversation can start fresh."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    request.session["profile"] = fresh_profile()
    request.session.modified = True
    return JsonResponse({"status": "reset"})


@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    data = json.loads(request.body)
    user_message = data.get("message", "").strip()

    if not user_message:
        return JsonResponse({"reply": "कृपया कुछ बोलिए।"})

    if "profile" not in request.session:
        request.session["profile"] = fresh_profile()

    current_profile = request.session["profile"]

    llm_json = detect_intent(user_message)

    intent = llm_json.get("intent", "incomplete")

    if "_error" in llm_json:
        return JsonResponse({"reply": PARSE_ERROR_MSG})

    if intent == "unrelated":
        return JsonResponse({"reply": UNRELATED_MSG})

    if intent == "specific_scheme":
        sid = llm_json.get("specific_scheme_id")
        scheme = engine.find_scheme(sid)
        if scheme:
            reply = format_scheme_detail(scheme)
        else:
            reply = "माफ़ करें, यह योजना हमारी सूची में नहीं है।"
        return JsonResponse({"reply": reply})

    # scheme_query / incomplete — update profile from what user said
    merge_profile(current_profile, engine.profile_from_llm_json(llm_json))
    request.session["profile"] = current_profile
    request.session.modified = True

    result = engine.evaluate_all(current_profile)
    eligible = result["eligible"]
    pending = result["pending"]

    reply = format_eligible_names(eligible)

    if pending:
        first = pending[0]
        question = engine._followup_question(first["skipped_fields"][0])
        reply += f" कुछ और योजनाएं हो सकती हैं। {first['name']} के लिए — {question}"
    elif intent == "incomplete":
        missing = engine.get_missing_fields(current_profile)
        if missing:
            reply += " " + engine._followup_question(missing[0])

    return JsonResponse({
        "reply": reply,
        "profile": current_profile,
    })
