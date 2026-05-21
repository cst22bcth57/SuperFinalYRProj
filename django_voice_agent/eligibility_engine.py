# eligibility_engine.py
# ---------------------------------------------------------------------------
# Three-bucket eligibility engine:
#
#   ELIGIBLE  — all rules checked, all passed (score >= 1)
#   PENDING   — some rules skipped because profile field was None
#               (needs follow-up question before confirming)
#   INELIGIBLE — at least one rule hard-failed → discarded silently
#
# Caller (main_pipeline.py) should:
#   1. Speak all ELIGIBLE schemes immediately
#   2. For each PENDING scheme, ask the missing field question,
#      then re-run after profile is updated
# ---------------------------------------------------------------------------

import json
import os


class SchemeEngine:

    def __init__(self, schemes_path: str):
        if not os.path.exists(schemes_path):
            raise FileNotFoundError(f"Schemes file not found: {schemes_path}")
        with open(schemes_path, "r", encoding="utf-8") as f:
            self.schemes = json.load(f)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def profile_from_llm_json(self, llm_output: dict) -> dict:
        """Converts raw LLM JSON into a clean typed profile dict."""
        extracted = llm_output.get("extracted", llm_output)
        return {
            "age":               self._safe_int(extracted.get("age")),
            "gender":            self._normalize(extracted.get("gender")),
            "caste":             self._normalize(extracted.get("caste")),
            "max_income_annual": self._safe_int(
                                    extracted.get("max_income_annual")
                                    or extracted.get("income_annual")
                                 ),
            "farmer":            extracted.get("farmer"),
            "marital_status":    self._normalize(extracted.get("marital_status")),
        }

    def evaluate_all(self, profile: dict) -> dict:
        """
        Main method. Returns a dict with three buckets:

        {
          "eligible": [
              { id, name, description, benefits, how_to_apply, helpline, score }
              ...
          ],
          "pending": [
              {
                id, name, score,
                "skipped_fields":   ["age", "caste"],   # profile fields that were None
                "followup_hi":      "आपकी जाति क्या है?"  # question to ask next
              }
              ...
          ],
          "ineligible": []   # discarded, not returned to caller
        }
        """
        eligible   = []
        pending    = []

        for scheme in self.schemes:
            result = self._evaluate(profile, scheme)

            if result["hard_failed"]:
                # At least one rule definitively failed → discard
                continue

            elif result["skipped_fields"]:
                # No hard failures but some rules were skipped (profile field was None)
                # → needs follow-up before confirming
                pending.append({
                    "id":             scheme["id"],
                    "name":           scheme["name"],
                    "score":          result["score"],
                    "skipped_fields": result["skipped_fields"],
                    "followup_hi":    self._followup_question(result["skipped_fields"][0]),
                })

            else:
                # All rules checked and passed → confirmed eligible
                # (score 0 with empty rules = open-to-all scheme like PMJDY → include)
                eligible.append({
                    "id":           scheme["id"],
                    "name":         scheme["name"],
                    "description":  scheme.get("description", ""),
                    "benefits":     scheme.get("benefits", ""),
                    "how_to_apply": scheme.get("how_to_apply", ""),
                    "helpline":     scheme.get("helpline", ""),
                    "score":        result["score"],
                })

        eligible.sort(key=lambda x: x["score"], reverse=True)
        pending.sort(key=lambda x: x["score"], reverse=True)

        return {"eligible": eligible, "pending": pending}

    def get_missing_fields(self, profile: dict) -> list:
        """Returns list of field names still None in the profile."""
        return [f for f, v in profile.items() if v is None]

    def find_scheme(self, scheme_id: str) -> dict | None:
        """
        Finds a scheme by id (exact) or alias (fuzzy).
        Used for specific_scheme intent lookups.
        """
        if not scheme_id:
            return None
        query = scheme_id.lower().strip()
        for scheme in self.schemes:
            if scheme["id"].lower() == query:
                return scheme
        for scheme in self.schemes:
            aliases = [a.lower() for a in scheme.get("aliases", [])]
            if any(query in alias or alias in query for alias in aliases):
                return scheme
        return None

    # ------------------------------------------------------------------
    # Internal Matching Logic
    # ------------------------------------------------------------------

    def _evaluate(self, profile: dict, scheme: dict) -> dict:
        """
        Evaluates one scheme against the profile.

        Returns:
        {
          "score":          int,        # rules checked AND passed
          "hard_failed":    bool,       # True if any rule definitively failed
          "skipped_fields": list[str],  # profile fields that were None (rule skipped)
        }
        """
        rules          = scheme.get("eligibility", {})
        score          = 0
        hard_failed    = False
        skipped_fields = []

        # --- age_min ---
        if "age_min" in rules:
            if profile["age"] is None:
                skipped_fields.append("age")
            elif profile["age"] < rules["age_min"]:
                hard_failed = True
            else:
                score += 1

        # --- age_max ---
        if "age_max" in rules:
            if profile["age"] is None:
                if "age" not in skipped_fields:
                    skipped_fields.append("age")
            elif profile["age"] > rules["age_max"]:
                hard_failed = True
            else:
                score += 1

        # --- gender ---
        if "gender" in rules:
            if profile["gender"] is None:
                skipped_fields.append("gender")
            elif profile["gender"].upper() != rules["gender"].upper():
                hard_failed = True
            else:
                score += 1

        # --- caste_in ---
        if "caste_in" in rules:
            if profile["caste"] is None:
                skipped_fields.append("caste")
            elif profile["caste"].upper() not in [c.upper() for c in rules["caste_in"]]:
                hard_failed = True
            else:
                score += 1

        # --- max_income_annual ---
        if "max_income_annual" in rules:
            if profile["max_income_annual"] is None:
                skipped_fields.append("max_income_annual")
            elif profile["max_income_annual"] > rules["max_income_annual"]:
                hard_failed = True
            else:
                score += 1

        # --- farmer ---
        if "farmer" in rules:
            if profile["farmer"] is None:
                skipped_fields.append("farmer")
            elif profile["farmer"] != rules["farmer"]:
                hard_failed = True
            else:
                score += 1

        # --- marital_status ---
        if "marital_status" in rules:
            if profile["marital_status"] is None:
                skipped_fields.append("marital_status")
            elif profile["marital_status"].lower() != rules["marital_status"].lower():
                hard_failed = True
            else:
                score += 1

        return {
            "score":          score,
            "hard_failed":    hard_failed,
            "skipped_fields": skipped_fields,
        }

    # ------------------------------------------------------------------
    # Follow-up Questions (Hindi)
    # ------------------------------------------------------------------

    FOLLOWUP_QUESTIONS = {
        "age":               "आपकी उम्र कितनी है?",
        "gender":            "आप पुरुष हैं या महिला?",
        "caste":             "आपकी जाति क्या है? जैसे SC, ST, OBC या सामान्य?",
        "max_income_annual": "आपकी सालाना आमदनी कितनी है?",
        "farmer":            "क्या आप किसान हैं?",
        "marital_status":    "आप विवाहित हैं, अविवाहित हैं, या विधवा हैं?",
    }

    def _followup_question(self, field: str) -> str:
        return self.FOLLOWUP_QUESTIONS.get(field, f"क्या आप अपना {field} बता सकते हैं?")


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_int(value):
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalize(value):
        return value.strip() if isinstance(value, str) and value.strip() else None


# ---------------------------------------------------------------------------
# Quick test  →  python eligibility_engine.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json

    engine = SchemeEngine("schemes.json")

    # Partial profile — age and income known, caste/marital unknown
    profile = engine.profile_from_llm_json({
        "extracted": {
            "age": 65,
            "gender": "M",
            "caste": None,            # unknown → will cause some schemes to go pending
            "max_income_annual": 150000,
            "farmer": True,
            "marital_status": None,   # unknown
        }
    })

    print("Profile:", profile)
    print()

    result = engine.evaluate_all(profile)

    print(f"✅ ELIGIBLE ({len(result['eligible'])} schemes):")
    for s in result["eligible"]:
        print(f"  [{s['score']} pts] {s['name']}")
        print(f"           {s['benefits']}")

    print(f"\n⏳ PENDING ({len(result['pending'])} schemes — need more info):")
    for s in result["pending"]:
        print(f"  [{s['score']} pts] {s['name']}")
        print(f"  Missing: {s['skipped_fields']}")
        print(f"  Ask: {s['followup_hi']}")
