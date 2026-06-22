# ============================================================
# CELL 1 — install dependencies
# ============================================================
!pip install -q google-genai requests


# ============================================================
# CELL 2 — secrets (set these up under Add-ons -> Secrets first)
# ============================================================
from kaggle_secrets import UserSecretsClient

user_secrets = UserSecretsClient()
GOOGLE_API_KEY = user_secrets.get_secret("GOOGLE_API_KEY")
RESEND_API_KEY = user_secrets.get_secret("RESEND_API_KEY")
RESEND_VERIFIED_EMAIL = user_secrets.get_secret("RESEND_VERIFIED_EMAIL")
DOCTOR_NAME = user_secrets.get_secret("DOCTOR_NAME")
DOCTOR_PHONE = user_secrets.get_secret("DOCTOR_PHONE")


# ============================================================
# CELL 3 — email sending via Resend's HTTP API (not SMTP - many
# hosted environments, including this project's production
# deployment on Render, block outbound SMTP ports entirely. Resend
# sends over normal HTTPS, so it isn't affected.)
# ============================================================
import requests


def send_email(subject: str, body: str) -> dict:
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": "onboarding@resend.dev",
            "to": [RESEND_VERIFIED_EMAIL],
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# CELL 4 — storage tools (log_checkin, get_history). These are
# deliberately the ONLY way anything touches stored data - no raw
# database/file access is ever exposed directly to the LLM, only
# these bounded functions.
# ============================================================
import json
import os
from datetime import date, datetime

DATA_DIR = "/kaggle/working/data"


def _person_file(person: str) -> str:
    safe_name = person.strip().lower().replace(" ", "_")
    return os.path.join(DATA_DIR, f"{safe_name}.json")


def log_checkin(
    person: str,
    food_today: str,
    blood_sugar: str,
    medication_taken: str,
    medication_stock: str,
    supplies_status: str,
    next_appointment: str,
    diet_followed: str,
    notes: str,
) -> dict:
    """
    Saves one check-in as a new row, with a real timestamp. Called
    DETERMINISTICALLY by our own code, never by the LLM - the date/time
    must always be exactly correct, which is not something to leave to
    a model (we previously saw a model write the literal word "today"
    instead of an actual date - fixed by removing that control entirely).
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now()

    entry = {
        "date": date.today().isoformat(),
        "timestamp": now.isoformat(),
        "food_today": food_today,
        "blood_sugar": blood_sugar,
        "medication_taken": medication_taken,
        "medication_stock": medication_stock,
        "supplies_status": supplies_status,
        "next_appointment": next_appointment,
        "diet_followed": diet_followed,
        "notes": notes,
    }

    path = _person_file(person)
    history = []
    if os.path.exists(path):
        with open(path, "r") as f:
            history = json.load(f)
    history.append(entry)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)

    return entry


def get_history(person: str, last_n: int = None) -> list:
    """Retrieve past check-ins, oldest first. This IS exposed to the
    LLM as a tool - it's read-only and scoped to one person at a time."""
    path = _person_file(person)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        history = json.load(f)
    if last_n is not None:
        history = history[-last_n:]
    return history


def send_alert(person: str, message: str, recipients: list[str], reason: str) -> dict:
    """The only way the agent can cause a real-world side effect
    (sending an email) - and even this is logged, not silent."""
    subject = f"Check-in alert for {person}: {reason}"
    send_email(subject=subject, body=message)
    print(f"[ALERT SENT] {person} - {reason}")
    return {"person": person, "message": message, "recipients": recipients, "reason": reason}


# ============================================================
# CELL 5 — deterministic emergency detection. This is intentionally
# NOT an LLM decision. For the one judgment in this whole system
# where being wrong has the highest real-world cost, a fixed,
# auditable rule is more trustworthy than asking a model to re-derive
# the right answer fresh each time.
# ============================================================
import time

LOW_THRESHOLD = 70
HIGH_THRESHOLD = 300
EMERGENCY_SYMPTOM_KEYWORDS = [
    "confusion", "confused", "fainting", "fainted", "faint",
    "chest pain", "difficulty breathing", "can't breathe",
    "unresponsive", "slurred speech", "seizure",
]
REPEAT_COUNT = 3
REPEAT_INTERVAL_SECONDS = 5  # shortened for this demo; real use ~300s


def is_emergency(blood_sugar, symptoms_text: str) -> bool:
    if blood_sugar is not None and (blood_sugar < LOW_THRESHOLD or blood_sugar > HIGH_THRESHOLD):
        return True
    text = symptoms_text.lower()
    return any(k in text for k in EMERGENCY_SYMPTOM_KEYWORDS)


def handle_emergency(person: str, blood_sugar, symptoms_text: str) -> None:
    log_checkin(
        person=person, food_today="not reported", blood_sugar=str(blood_sugar),
        medication_taken="not reported", medication_stock="not reported",
        supplies_status="not reported", next_appointment="not reported",
        diet_followed="not reported", notes=f"EMERGENCY: {symptoms_text}",
    )

    for attempt in range(1, REPEAT_COUNT + 1):
        body = (
            f"{person} may be having a medical emergency.\n\n"
            f"Blood sugar reading: {blood_sugar}\n"
            f"Symptoms/notes: {symptoms_text}\n\n"
            f"Please call {DOCTOR_NAME} at {DOCTOR_PHONE}, or call emergency "
            f"services, right away."
        )
        send_email(
            subject=f"URGENT: possible medical emergency for {person} ({attempt}/{REPEAT_COUNT})",
            body=body,
        )
        print(f"[EMERGENCY EMAIL {attempt}/{REPEAT_COUNT}] sent for {person}")
        if attempt < REPEAT_COUNT:
            time.sleep(REPEAT_INTERVAL_SECONDS)


# ============================================================
# CELL 6 — the agent itself. Only gets called for NON-emergency days.
# Notice it only has two tools: get_history and send_alert. It does
# NOT have log_checkin - logging today's entry already happened
# deterministically before this runs, so the model's only real job
# is the judgment call: does this need an alert, and if so, what
# should it say.
# ============================================================
from google import genai
from google.genai import types

client = genai.Client(api_key=GOOGLE_API_KEY)

SYSTEM_INSTRUCTION = """
You are a family check-in assistant. True medical emergencies are
already handled separately before you are called - you will only ever
see normal-range check-ins. Today's check-in has ALREADY been saved to
the database before you were called - do NOT try to log it again.
Your only job is the judgment call:

1. Call get_history(person) to see their recent pattern (this includes
   today's just-saved entry too, at the end).
2. Decide whether anything needs an alert, using these rules:
   - Medication missed (today, or repeatedly in history) -> alert-worthy
   - Medication or supplies running low -> alert-worthy
   - Blood sugar over 135 mg/dL, or trending up across recent history
     -> alert-worthy
   - Next appointment within 3 days -> alert-worthy (reminder, not urgent)
   - A diet contradiction (said fine, but wasn't) -> only alert-worthy
     if it's part of a repeated pattern
3. If something is alert-worthy, call send_alert EXACTLY ONCE, combining
   every issue into one message as bullet points. Recipients = ["me",
   "family"] if medication/blood-sugar related, otherwise ["me"].
4. Do NOT call send_alert if nothing meets the bar - most days should
   have no alert.
5. Always finish with a short plain-language summary of the day.
"""


def run_checkin(person: str, call_notes: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Today's check-in for {person} (already saved): {call_notes}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[get_history, send_alert],
        ),
    )

    print("--- Tool calls made by the agent ---")
    for call in response.automatic_function_calling_history or []:
        for part in (call.parts or []):
            if getattr(part, "function_call", None):
                print(" ", part.function_call.name, dict(part.function_call.args or {}))
    print("-------------------------------------")

    return response.text


# ============================================================
# CELL 7 — the full flow, mirroring exactly what the production
# Flask backend does: deterministic emergency check FIRST, only
# falling through to the agent if it's not an emergency.
# ============================================================
def process_checkin(person, medication_taken, blood_sugar, feeling, notes):
    symptoms_text = f"{feeling} {notes}".strip()

    if is_emergency(blood_sugar, symptoms_text):
        print(f"=== EMERGENCY PATH (no LLM involved) for {person} ===")
        handle_emergency(person, blood_sugar, symptoms_text)
        return "Emergency detected - family notified directly, agent was not used for this decision."

    clean_notes = notes.strip() if notes.strip() else "(no additional notes)"
    if feeling and feeling.lower() != "good":
        clean_notes = f"Feeling: {feeling}. {clean_notes}"

    log_checkin(
        person=person, food_today="not collected", blood_sugar=str(blood_sugar),
        medication_taken=medication_taken, medication_stock="not collected",
        supplies_status="not collected", next_appointment="not collected",
        diet_followed="not collected", notes=clean_notes,
    )

    call_notes = f"Medication: {medication_taken}. Blood sugar: {blood_sugar}. Notes: {clean_notes}"
    print(f"=== AGENT PATH (Gemini reasoning) for {person} ===")
    summary = run_checkin(person, call_notes)
    print()
    print("=== Agent summary ===")
    print(summary)
    return summary


# ============================================================
# CELL 8 — Scenario 1: a normal day. Expect: no alert.
# ============================================================
process_checkin(
    person="Mom",
    medication_taken="Yes, all of it",
    blood_sugar=120,
    feeling="Good",
    notes="",
)


# ============================================================
# CELL 9 — Scenario 2: needs attention. Expect: one consolidated
# alert email, not three separate ones.
# ============================================================
process_checkin(
    person="Mom",
    medication_taken="Missed one dose",
    blood_sugar=180,
    feeling="Tired",
    notes="felt a bit off after lunch",
)


# ============================================================
# CELL 10 — Scenario 3: the same issue again. Expect: the summary
# should reflect the PATTERN (missed twice), since the agent pulls
# history before deciding - not just looking at today alone.
# ============================================================
process_checkin(
    person="Mom",
    medication_taken="Missed it today",
    blood_sugar=200,
    feeling="Tired",
    notes="completely forgot today too",
)


# ============================================================
# CELL 11 — Scenario 4: a true emergency. Expect: this bypasses the
# LLM entirely - the print statements above will show "EMERGENCY
# PATH (no LLM involved)" rather than any agent reasoning.
# ============================================================
process_checkin(
    person="Mom",
    medication_taken="Missed it today",
    blood_sugar=40,
    feeling="Not great",
    notes="felt confused and dizzy",
)
