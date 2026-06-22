"""
db_tools.py

Postgres-backed versions of the same three tools (log_checkin,
get_history, send_alert). Same logic as before - only the storage layer
changed (MongoDB -> Postgres/Neon), after MongoDB Atlas's login system
became unreliable. Nothing outside this file needed to change.

Uses a single "checkins" table (one row per person per day) and a single
"alerts" table (one row per alert sent).
"""

import os
from datetime import date, datetime

import psycopg2
import psycopg2.extras

from email_sender import send_email


def get_conn():
    """New connection per call - simplest approach for this project's traffic level."""
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call every startup.
    NOTE: if you already created the old schema (with a UNIQUE(person, date)
    constraint), this won't update it automatically - drop the table once
    manually in Neon's SQL Editor first: DROP TABLE checkins;"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS checkins (
                    id SERIAL PRIMARY KEY,
                    person TEXT NOT NULL,
                    date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    food_today TEXT,
                    blood_sugar TEXT,
                    medication_taken TEXT,
                    medication_stock TEXT,
                    supplies_status TEXT,
                    next_appointment TEXT,
                    diet_followed TEXT,
                    notes TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    person TEXT NOT NULL,
                    message TEXT,
                    recipients TEXT,
                    sent_to_addresses TEXT,
                    reason TEXT,
                    sent_at TEXT
                )
            """)
        conn.commit()
    finally:
        conn.close()


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
    """Save one check-in as a NEW row - every submission is kept, even
    multiple in the same day, each with its own real timestamp. (Earlier
    versions overwrote same-day entries - fixed after noticing a second
    check-in the same day silently replaced the first.)"""
    now = datetime.now()
    entry = {
        "person": person,
        "date": check_date if check_date is not None else date.today().isoformat(),
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

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO checkins (person, date, timestamp, food_today, blood_sugar,
                    medication_taken, medication_stock, supplies_status,
                    next_appointment, diet_followed, notes)
                VALUES (%(person)s, %(date)s, %(timestamp)s, %(food_today)s, %(blood_sugar)s,
                    %(medication_taken)s, %(medication_stock)s, %(supplies_status)s,
                    %(next_appointment)s, %(diet_followed)s, %(notes)s)
                """,
                entry,
            )
        conn.commit()
    finally:
        conn.close()

    return entry


def get_history(person: str, last_n: int = None) -> list:
    """Retrieve past check-in entries for a person, oldest first (by exact
    timestamp, so same-day entries are still ordered correctly)."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT person, date, timestamp, food_today, blood_sugar, medication_taken,
                       medication_stock, supplies_status, next_appointment,
                       diet_followed, notes
                FROM checkins WHERE person = %s ORDER BY timestamp ASC
                """,
                (person,),
            )
            history = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    if last_n is not None:
        history = history[-last_n:]

    return history


def send_alert(person: str, message: str, recipients: list[str], reason: str) -> dict:
    """Send an alert by email (via Resend's HTTP API - see email_sender.py
    for why this isn't SMTP), and log it to Postgres."""
    subject = f"Check-in alert for {person}: {reason}"
    send_email(subject=subject, body=message)

    sent_at = date.today().isoformat()

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts (person, message, recipients, sent_to_addresses, reason, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (person, message, ",".join(recipients), os.environ.get("RESEND_VERIFIED_EMAIL", ""), reason, sent_at),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "person": person,
        "message": message,
        "recipients": recipients,
        "sent_to_addresses": [os.environ.get("RESEND_VERIFIED_EMAIL", "")],
        "reason": reason,
        "sent_at": sent_at,
    }
