# ============================================================
# CELL 1 — install the SDK (Kaggle may not have it pre-installed)
# ============================================================
!pip install -q google-genai


# ============================================================
# CELL 2 — get the API key from Kaggle Secrets (never typed here)
# ============================================================
from kaggle_secrets import UserSecretsClient

user_secrets = UserSecretsClient()
GOOGLE_API_KEY = user_secrets.get_secret("GOOGLE_API_KEY")
GMAIL_ADDRESS = user_secrets.get_secret("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = user_secrets.get_secret("GMAIL_APP_PASSWORD")


# ============================================================
# CELL 3 — the three tools (same logic as tools.py, paths adjusted
# for Kaggle's writable /kaggle/working directory)
# ============================================================
import json
import os
from datetime import date

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
    check_date: str = None,
) -> dict:
    """
    Save one day's check-in for a person. Fields are short plain-text
    descriptions (e.g. medication_taken="took morning dose, missed evening")
    rather than strict yes/no.
    """
    if check_date is None:
        check_date = date.today().isoformat()

    entry = {
        "date": check_date,
        "food_today": food_today,
        "blood_sugar": blood_sugar,
        "medication_taken": medication_taken,
        "medication_stock": medication_stock,
        "supplies_status": supplies_status,
        "next_appointment": next_appointment,
        "diet_followed": diet_followed,
        "notes": notes,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    path = _person_file(person)

    if os.path.exists(path):
        with open(path, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append(entry)

    with open(path, "w") as f:
        json.dump(history, f, indent=2)

    return entry


def get_history(person: str, last_n: int = None) -> list:
    """Retrieve past check-in entries for a person, oldest first."""
    path = _person_file(person)

    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        history = json.load(f)

    if last_n is not None:
        history = history[-last_n:]

    return history


ALERTS_LOG = os.path.join(DATA_DIR, "alerts_log.json")


def send_alert(person: str, message: str, recipients: list[str], reason: str) -> dict:
    """
    Send an alert about a person to one or more recipients, by real email
    (Gmail SMTP), and log it. `recipients` uses short labels ("me",
    "family") looked up in RECIPIENT_EMAILS for the actual address.
    """
    import smtplib
    from email.mime.text import MIMEText

    RECIPIENT_EMAILS = {
        "me": "your-email@example.com",
        "family": "your-email@example.com",
    }

    to_addresses = [RECIPIENT_EMAILS[r] for r in recipients if r in RECIPIENT_EMAILS]

    subject = f"Check-in alert for {person}: {reason}"
    email_msg = MIMEText(message)
    email_msg["Subject"] = subject
    email_msg["From"] = GMAIL_ADDRESS
    email_msg["To"] = ", ".join(to_addresses)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_addresses, email_msg.as_string())

    alert = {
        "person": person,
        "message": message,
        "recipients": recipients,
        "sent_to_addresses": to_addresses,
        "reason": reason,
        "sent_at": date.today().isoformat(),
    }

    print("=" * 50)
    print(f"EMAIL SENT for {person} ({reason})")
    print(f"To: {', '.join(to_addresses)}")
    print(message)
    print("=" * 50)

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(ALERTS_LOG):
        with open(ALERTS_LOG, "r") as f:
            log = json.load(f)
    else:
        log = []

    log.append(alert)

    with open(ALERTS_LOG, "w") as f:
        json.dump(log, f, indent=2)

    return alert


# ============================================================
# CELL 4 — the agent itself
# ============================================================
from google import genai
from google.genai import types

client = genai.Client(api_key=GOOGLE_API_KEY)

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
5. Do NOT call send_alert at all if nothing meets the bar above - most
   days should have no alert, to avoid alert fatigue.
6. Always finish with a short plain-language summary of the day, for the
   caregiver reading this later: what happened, anything flagged, and why.
"""


def run_checkin(call_notes: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=call_notes,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[log_checkin, get_history, send_alert],
        ),
    )

    print("--- Tool calls made by the agent ---")
    for call in response.automatic_function_calling_history or []:
        print(call)
    print("-------------------------------------")

    return response.text


# ============================================================
# CELL 5 — run one example day
# ============================================================
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


# ============================================================
# CELL 6 — Day 2 for Mom: builds on yesterday's pattern.
# Expect: get_history should now return yesterday's entry, and the agent
# should recognize medication has now been missed 2 days running AND
# stock has hit zero — likely a more urgent alert than Day 1.
# ============================================================
notes_day2 = (
    "Call with Mom today. She had oatmeal for breakfast and a salad for "
    "lunch. Blood sugar was 185. She forgot her evening medication dose "
    "again. She mentioned she's now completely out of medication, no "
    "pills left at all. Test strips are still fine. She said she skipped "
    "dessert today. She sounded a bit more tired than usual but otherwise "
    "okay."
)

summary_day2 = run_checkin(notes_day2)
print()
print("=== Agent summary (Day 2, Mom) ===")
print(summary_day2)


# ============================================================
# CELL 7 — A quiet, normal day, with Dad (no prior history at all).
# Expect: get_history returns empty (first entry for Dad), log_checkin
# saves it, and send_alert should NOT be called - nothing here meets
# the alert bar. This proves the agent doesn't over-alert.
# ============================================================
notes_quiet_day = (
    "Call with Dad today. He had a balanced breakfast, lunch, and "
    "dinner. Blood sugar was 110, which is normal for him. He took both "
    "his morning and evening medication on time. He has plenty of "
    "medication left, about 3 weeks' supply. Test strips are well "
    "stocked. He's been following his diet well. No appointment "
    "scheduled in the near term. He sounded cheerful and energetic."
)

summary_quiet = run_checkin(notes_quiet_day)
print()
print("=== Agent summary (quiet day, Dad) ===")
print(summary_quiet)
