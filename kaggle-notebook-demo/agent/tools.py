"""
tools.py

Tools the agent can call.

Each tool is a plain Python function, kept simple and independent so it can
be tested entirely on its own before being wired into the agent loop.
This file currently has just one tool: log_checkin().
"""

import json
import os
from datetime import date

# All check-in history is stored as one JSON file per person, e.g.
# data/mom.json, data/dad.json
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _person_file(person: str) -> str:
    """Turn a person's name into a safe file path, e.g. 'Mom' -> data/mom.json"""
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
    Save one day's check-in for a person.

    Fields are short, plain-text descriptions rather than strict yes/no,
    e.g. medication_taken="took morning dose, missed evening dose".
    This keeps the data easy to read and easy for the agent to reason
    about later, without forcing every detail into a rigid yes/no box.

    Args:
        person: who this check-in is for, e.g. "Mom"
        food_today: what they ate today
        blood_sugar: reported blood sugar reading
        medication_taken: short status of medication adherence today
        medication_stock: short status of medication supply
        supplies_status: short status of medical supplies (e.g. test strips)
        next_appointment: date of next doctor's appointment, if known
        diet_followed: short status of whether the recommended diet was followed
        notes: anything else from the call, especially details that came up
               later in conversation rather than as a direct answer
        check_date: date of this check-in (defaults to today)

    Returns:
        The saved entry, as a dict, so callers/tests can confirm what was stored.
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

    # Load existing history (if any), then append today's entry
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
    """
    Retrieve past check-in entries for a person, oldest first.

    This is what lets the agent spot patterns over time (e.g. medication
    missed two days running, blood sugar trending up) instead of only
    ever looking at a single day in isolation.

    Args:
        person: who to retrieve history for, e.g. "Mom"
        last_n: if given, only return the most recent N entries.
                If omitted, returns the full history.

    Returns:
        A list of entry dicts (same shape as log_checkin's return value).
        Returns an empty list if no history exists yet for this person.
    """
    path = _person_file(person)

    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        history = json.load(f)

    if last_n is not None:
        history = history[-last_n:]

    return history


# Alerts are simulated for now: printed clearly and logged to a file, as if
# sent. This lets us build and test the full agent flow without needing
# email/SMS credentials yet. Swapping in real Gmail sending later only
# requires changing the inside of this one function.
ALERTS_LOG = os.path.join(DATA_DIR, "alerts_log.json")


def send_alert(person: str, message: str, recipients: list[str], reason: str) -> dict:
    """
    Send an alert about a person to one or more recipients, by real email
    (Gmail SMTP), and log it.

    `recipients` uses short labels like "me" or "family" - these are
    looked up in RECIPIENT_EMAILS to find the actual email address to
    send to. This keeps the agent's reasoning simple (it just says who
    conceptually should be notified) while the actual addresses live in
    one place, set via environment variables / Kaggle Secrets.

    Args:
        person: who the alert is about, e.g. "Mom"
        message: the alert text itself
        recipients: labels of who should receive it, e.g. ["me", "family"]
        reason: short label for why this alert was triggered

    Returns:
        The alert record that was logged, including which addresses it
        was actually sent to.
    """
    import smtplib
    from email.mime.text import MIMEText

    sender_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    # Map short labels to real email addresses. Fill these in with the
    # actual addresses that should receive alerts.
    RECIPIENT_EMAILS = {
        "me": "your-email@example.com",
        "family": "your-email@example.com",
    }

    to_addresses = [RECIPIENT_EMAILS[r] for r in recipients if r in RECIPIENT_EMAILS]

    subject = f"Check-in alert for {person}: {reason}"
    email_msg = MIMEText(message)
    email_msg["Subject"] = subject
    email_msg["From"] = sender_address
    email_msg["To"] = ", ".join(to_addresses)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_address, app_password)
        server.sendmail(sender_address, to_addresses, email_msg.as_string())

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
