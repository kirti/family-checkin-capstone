"""
emergency.py

Emergency detection is deliberately NOT left to the LLM's judgment alone.
This module checks fixed, deterministic thresholds in plain Python -
same result every time, no ambiguity - and handles the escalation
(repeated alerts to all family, with doctor/ambulance guidance) entirely
separately from the normal day-to-day agent reasoning.

Defaults below are general danger-zone numbers, NOT a substitute for
Mom/Dad's doctor's specific guidance - replace with his numbers if given.
"""

import os
import threading
import time
from datetime import date

from email_sender import send_email

LOW_THRESHOLD = 70
HIGH_THRESHOLD = 300

EMERGENCY_SYMPTOM_KEYWORDS = [
    "confusion", "confused", "fainting", "fainted", "faint",
    "chest pain", "difficulty breathing", "can't breathe",
    "unresponsive", "slurred speech", "seizure",
]

# NOTE: kept as documentation of the intended recipients, but emails
# currently all go to RESEND_VERIFIED_EMAIL only (see email_sender.py) -
# Resend can't send to other addresses without a verified domain.
EMERGENCY_RECIPIENTS = [
    e.strip() for e in os.environ.get("EMERGENCY_EMAILS", "").split(",") if e.strip()
]
DOCTOR_NAME = os.environ.get("DOCTOR_NAME", "your doctor")
DOCTOR_PHONE = os.environ.get("DOCTOR_PHONE", "")

# How long to wait between repeats, in seconds. Real-world use should be
# ~300 (5 minutes); for a demo video, set EMERGENCY_REPEAT_INTERVAL_SECONDS
# in the environment to something short (e.g. 5) so it's watchable on camera.
REPEAT_INTERVAL_SECONDS = int(os.environ.get("EMERGENCY_REPEAT_INTERVAL_SECONDS", 300))
REPEAT_COUNT = 3


def is_emergency(blood_sugar: int | None, symptoms_text: str) -> bool:
    """Pure, deterministic check - same answer every time for the same input."""
    if blood_sugar is not None and (blood_sugar < LOW_THRESHOLD or blood_sugar > HIGH_THRESHOLD):
        return True

    text = symptoms_text.lower()
    return any(keyword in text for keyword in EMERGENCY_SYMPTOM_KEYWORDS)


def _send_one_emergency_email(person: str, body: str, attempt: int) -> None:
    subject = f"URGENT: possible medical emergency for {person} ({attempt}/{REPEAT_COUNT})"
    send_email(subject=subject, body=body)


def _build_message(person: str, blood_sugar, symptoms_text: str, attempt: int) -> str:
    base = (
        f"{person} may be having a medical emergency.\n\n"
        f"Blood sugar reading: {blood_sugar if blood_sugar is not None else 'not reported'}\n"
        f"Symptoms/notes: {symptoms_text or 'none reported'}\n\n"
        f"Please call {DOCTOR_NAME} at {DOCTOR_PHONE}, or call emergency "
        f"services, right away.\n"
    )
    if attempt == 1:
        return base
    if attempt < REPEAT_COUNT:
        return f"REMINDER ({attempt}/{REPEAT_COUNT}) - please respond.\n\n{base}"
    return f"FINAL REMINDER ({attempt}/{REPEAT_COUNT}) - please respond or call 911/emergency services.\n\n{base}"


def _repeat_send_in_background(person: str, blood_sugar, symptoms_text: str) -> None:
    for attempt in range(1, REPEAT_COUNT + 1):
        body = _build_message(person, blood_sugar, symptoms_text, attempt)
        try:
            _send_one_emergency_email(person, body, attempt)
        except Exception as e:
            # Don't let a single failed send kill the remaining repeats
            print(f"Emergency email attempt {attempt} failed: {e}")
        if attempt < REPEAT_COUNT:
            time.sleep(REPEAT_INTERVAL_SECONDS)


def handle_emergency(person: str, blood_sugar, symptoms_text: str, db_log_fn) -> dict:
    """
    Logs the emergency check-in immediately, then sends the first alert
    right away and kicks off the remaining repeats in a background thread
    so the web request can return to the user immediately rather than
    waiting through all 3 sends.
    """
    db_log_fn(
        person=person,
        food_today="not reported",
        blood_sugar=str(blood_sugar) if blood_sugar is not None else "not reported",
        medication_taken="not reported",
        medication_stock="not reported",
        supplies_status="not reported",
        next_appointment="not reported",
        diet_followed="not reported",
        notes=f"EMERGENCY: {symptoms_text}",
        check_date=date.today().isoformat(),
    )

    thread = threading.Thread(
        target=_repeat_send_in_background,
        args=(person, blood_sugar, symptoms_text),
        daemon=True,
    )
    thread.start()

    return {
        "tier": "emergency",
        "message": (
            f"This looks like it may be a medical emergency. Family has "
            f"been notified and advised to call {DOCTOR_NAME} or "
            f"emergency services."
        ),
    }
