"""
agent_logic.py

Handles the normal-day reasoning (good day / needs attention tiers).
True emergencies are handled separately and deterministically in
emergency.py, before this code ever runs - so this only needs to worry
about the calmer, judgment-based decisions.
"""

import os

from google import genai
from google.genai import types

from db_tools import get_history, send_alert

_client = None


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


SYSTEM_INSTRUCTION = """
You are a family check-in assistant. True medical emergencies are
already handled separately before you are called - you will only ever
see normal-range check-ins. Today's check-in has ALREADY been saved to
the database before you were called - do NOT try to log it again, it's
already done. Your only job here is the judgment call:

1. Call get_history(person) to see their recent pattern (this includes
   today's just-saved entry too, at the end).
2. Decide whether anything needs an alert, using these rules:
   - Medication missed (today, or repeatedly in history) -> alert-worthy
   - Medication or supplies running low -> alert-worthy
   - Blood sugar over 135 mg/dL, or trending up across recent history
     -> alert-worthy
   - Next appointment is within 3 days -> alert-worthy (reminder, not urgent)
   - A diet contradiction (said fine, but wasn't) -> only alert-worthy if
     it's part of a repeated pattern, otherwise just mention it in the
     summary
3. If one or more things above are alert-worthy, call send_alert EXACTLY
   ONCE - never more than once. Combine every alert-worthy item into a
   single short message, as separate bullet points.
   Set recipients to ["me", "family"] if any medication or blood-sugar
   issue is present; otherwise just ["me"].
4. Do NOT call send_alert at all if nothing meets the bar above - most
   days should have no alert, to avoid alert fatigue.
5. Always finish with a short plain-language summary of the day.
"""


def run_checkin(person: str, call_notes: str) -> dict:
    """
    Process one (non-emergency) day's notes through the agent. Today's
    entry must already be logged via db_tools.log_checkin BEFORE calling
    this - this function only judges whether to alert, it never writes
    the check-in data itself (that's now deterministic, done in app.py).
    Returns a dict with the tier-ish info the frontend can show.
    """
    client = get_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Today's check-in for {person} (already saved): {call_notes}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[get_history, send_alert],
        ),
    )

    alert_fired = any(
        getattr(part, "function_call", None) and part.function_call.name == "send_alert"
        for call in (response.automatic_function_calling_history or [])
        for part in (call.parts or [])
    )

    return {
        "tier": "needs_attention" if alert_fired else "good",
        "message": response.text,
    }
