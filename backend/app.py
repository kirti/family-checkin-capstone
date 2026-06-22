"""
app.py

The backend API. Three endpoints:
  GET  /api/health              - simple check that the server is alive
  POST /api/checkin             - receives a check-in from the web form
  GET  /api/history/<person>    - returns history for the chart pages

Every check-in goes through the deterministic emergency check FIRST.
Only if it's NOT an emergency does it go to the Gemini-based agent for
the calmer good-day / needs-attention judgment call.
"""

import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from db_tools import log_checkin, get_history, init_db
from emergency import is_emergency, handle_emergency
from agent_logic import run_checkin
from classify import classify_tier
from auth import init_auth_tables, attempt_login, require_auth

app = Flask(__name__)
# Allow requests from any origin for now (simplest for a personal-use demo).
# Tighten this to your specific GitHub Pages URL before sharing more widely.
CORS(app)

# Create tables if they don't exist yet. Wrapped in try/except so a
# temporary database hiccup at startup doesn't crash the whole server -
# /api/health will still work, and real errors will surface clearly on
# the first actual /api/checkin or /api/history call instead.
try:
    init_db()
    init_auth_tables()
except Exception as e:
    print(f"Warning: could not initialize database tables at startup: {e}")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")

    token = attempt_login(username, password)
    if token is None:
        return jsonify({"error": "Invalid username or password, or too many attempts - try again later"}), 401

    return jsonify({"token": token})


@app.route("/api/checkin", methods=["POST"])
@require_auth
def checkin():
    data = request.get_json(force=True)

    person = data.get("person", "Unknown")
    medication_taken = data.get("medication_taken", "")
    feeling = data.get("feeling", "")
    notes = data.get("notes", "")

    raw_blood_sugar = data.get("blood_sugar", "")
    try:
        blood_sugar = int(raw_blood_sugar)
    except (TypeError, ValueError):
        blood_sugar = None

    symptoms_text = f"{feeling} {notes}".strip()

    # Deterministic safety check happens BEFORE any LLM call.
    if is_emergency(blood_sugar, symptoms_text):
        result = handle_emergency(person, blood_sugar, symptoms_text, log_checkin)
        return jsonify(result)

    # Build a clean notes field ourselves - never let the LLM rewrite or
    # echo this, so it stays exactly as the person actually wrote it.
    clean_notes = notes.strip() if notes.strip() else "(no additional notes)"
    if feeling and feeling.lower() != "good":
        clean_notes = f"Feeling: {feeling}. {clean_notes}"

    # Log today's entry deterministically - this is already clean,
    # structured data from the form, so there's no need for an LLM to
    # "extract" anything here. Fields the self-fill form doesn't collect
    # (food, diet, appointment, stock, supplies) are explicitly marked,
    # rather than left for the model to guess at or fabricate.
    log_checkin(
        person=person,
        food_today="not collected (self-fill check-in)",
        blood_sugar=str(blood_sugar) if blood_sugar is not None else "not reported",
        medication_taken=medication_taken,
        medication_stock="not collected (self-fill check-in)",
        supplies_status="not collected (self-fill check-in)",
        next_appointment="not collected (self-fill check-in)",
        diet_followed="not collected (self-fill check-in)",
        notes=clean_notes,
    )

    call_notes = (
        f"Medication: {medication_taken}. "
        f"Blood sugar: {blood_sugar if blood_sugar is not None else 'not reported'}. "
        f"Notes: {clean_notes}"
    )

    result = run_checkin(person, call_notes)
    return jsonify(result)


@app.route("/api/history/<person>")
@require_auth
def history(person):
    range_param = request.args.get("range", "week")
    last_n = 7 if range_param == "week" else 30

    entries = get_history(person, last_n=last_n)
    for entry in entries:
        entry["tier"] = classify_tier(entry)

    return jsonify(entries)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
