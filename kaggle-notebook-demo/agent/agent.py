"""
agent.py

The agent itself. Gemini is given the three tools (log_checkin, get_history,
send_alert) and a system instruction describing the policy for when to
alert. Gemini decides on its own which tools to call, in what order, based
on the day's call notes and the person's history.

This uses the SDK's automatic function calling: we hand Gemini the actual
Python functions, and it calls them itself as needed, instead of us
manually wiring up call -> execute -> respond.

Run with: python agent/agent.py
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import log_checkin, get_history, send_alert

load_dotenv()

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

SYSTEM_INSTRUCTION = """
You are a family check-in assistant. Each day, you receive call notes from
a conversation with an elderly parent (structured answers plus free-form
notes from the rest of the call). Your job:

1. Call get_history(person) first, to see their recent pattern.
2. Call log_checkin(...) to save today's entry. Fill every field using the
   call notes given to you. If the free-form notes contain a detail that
   contradicts or updates a structured answer (e.g. they said their diet
   was fine but later mentioned eating something they shouldn't), reflect
   that accurately in the relevant field and in notes.
3. Decide whether anything needs an alert, using these rules:
   - Medication missed (today, or repeatedly in history) -> alert-worthy
   - Medication or supplies running low -> alert-worthy
   - Blood sugar reading is abnormal, or trending up/down across recent
     history -> alert-worthy
   - Next appointment is within 3 days -> alert-worthy (reminder, not urgent)
   - A diet contradiction (said fine, but wasn't) -> only alert-worthy if
     it's part of a repeated pattern, otherwise just mention it in the
     summary
4. If one or more things above are alert-worthy, call send_alert EXACTLY
   ONCE for the day - never more than once. Combine every alert-worthy
   item into a single short message, as separate bullet points, e.g.:
     - Missed evening medication (2nd day in a row)
     - Medication stock: out, refill needed
     - Appointment in 2 days (June 22)
   Set recipients to ["me", "family"] if any medication or blood-sugar
   issue is present; otherwise just ["me"] (e.g. only an appointment
   reminder). Set reason to a short label for the most significant issue.
5. Do NOT call send_alert at all if nothing meets the bar above — most
   days should have no alert, to avoid alert fatigue.
6. Always finish with a short plain-language summary of the day, for the
   caregiver reading this later: what happened, anything flagged, and why.
"""


def run_checkin(call_notes: str) -> str:
    """
    Process one day's call notes through the agent.

    Args:
        call_notes: free text describing today's call - can mix structured
                    answers and free-form details, exactly as you'd jot
                    them down after a real call.

    Returns:
        The agent's final plain-language summary of the day.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=call_notes,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[log_checkin, get_history, send_alert],
        ),
    )

    # This shows every tool call Gemini made along the way - useful for
    # the demo video, to show the agent's reasoning/tool-use process.
    print("--- Tool calls made by the agent ---")
    for call in response.automatic_function_calling_history or []:
        print(call)
    print("-------------------------------------")

    return response.text


if __name__ == "__main__":
    notes = (
        "Call with Mom today. She said she had toast for breakfast and "
        "a sandwich for lunch, then mentioned later she also had some "
        "ice cream in the evening. Blood sugar was 170. She took her "
        "morning medication but said she forgot the evening dose again. "
        "Medication is running low, maybe enough for 2 more days. Test "
        "strips are fine. Next appointment is in 2 days, on June 22nd. "
        "She sounded tired but in good spirits."
    )

    summary = run_checkin(notes)
    print()
    print("=== Agent summary ===")
    print(summary)
