"""
classify.py

Classifies a saved history entry into good / needs_attention / emergency,
purely for displaying past entries on the chart (color-coding). This is
NOT used to make live alerting decisions - that already happened at the
time each entry was logged (emergency.py for emergencies, agent_logic.py
for everything else). This is just "looking back" at what already happened.
"""

from emergency import LOW_THRESHOLD, HIGH_THRESHOLD, EMERGENCY_SYMPTOM_KEYWORDS


def classify_tier(entry: dict) -> str:
    raw_bs = entry.get("blood_sugar")
    try:
        blood_sugar = int(raw_bs)
    except (TypeError, ValueError):
        blood_sugar = None

    text = f"{entry.get('notes', '')} {entry.get('medication_taken', '')}".lower()

    if blood_sugar is not None and (blood_sugar < LOW_THRESHOLD or blood_sugar > HIGH_THRESHOLD):
        return "emergency"
    if any(keyword in text for keyword in EMERGENCY_SYMPTOM_KEYWORDS):
        return "emergency"
    if (blood_sugar is not None and blood_sugar > 135) or "missed" in text:
        return "needs_attention"
    return "good"
