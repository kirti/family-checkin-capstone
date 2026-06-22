"""
generate_dummy_data.py

Generates a realistic 1-month (30 day) dummy check-in history for Mom and
Dad, deliberately covering all 3 tiers:
  - Good day        : blood sugar <= 135, meds taken, nothing wrong
  - Needs attention  : blood sugar 136-300, OR missed meds/low stock/
                        upcoming appointment
  - Emergency        : blood sugar < 70 or > 300, OR a symptom mention

This is synthetic data for testing/demo purposes only - not real
check-ins. Output goes to data/mom_dummy_month.json and
data/dad_dummy_month.json (full month), and a _week.json version of each
(just the last 7 days) for a shorter demo/chart view.

Run with: python agent/generate_dummy_data.py
"""

import json
import os
import random
from datetime import date, timedelta

random.seed(42)  # reproducible output

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def classify_tier(blood_sugar: int, medication_taken: str, symptoms: str) -> str:
    """Same logic the agent uses, applied here just to label the dummy data."""
    emergency_symptoms = ["confusion", "fainting", "chest pain",
                           "difficulty breathing", "unresponsive"]
    if blood_sugar < 70 or blood_sugar > 300:
        return "emergency"
    if any(s in symptoms.lower() for s in emergency_symptoms):
        return "emergency"
    if blood_sugar > 135 or "missed" in medication_taken.lower():
        return "needs_attention"
    return "good"


def generate_day(person: str, day_date: date, force_tier: str = None) -> dict:
    """Generate one day's entry. force_tier lets us guarantee certain days
    hit a specific tier, so the dummy month isn't left to pure chance."""

    if force_tier == "emergency":
        blood_sugar = random.choice([55, 62, 320, 340])
        medication_taken = "took morning dose, took evening dose"
        symptoms = random.choice(["felt dizzy and confused", "nearly fainted"])
    elif force_tier == "needs_attention":
        blood_sugar = random.randint(150, 260)
        medication_taken = random.choice([
            "took morning dose, missed evening dose",
            "took morning dose, took evening dose",
        ])
        symptoms = "felt a bit tired"
    else:  # good day
        blood_sugar = random.randint(95, 135)
        medication_taken = "took morning dose, took evening dose"
        symptoms = "felt fine, in good spirits"

    medication_stock = random.choice(
        ["ok, about 2 weeks left"] * 5 + ["low, about 3 days left"]
    )
    supplies_status = random.choice(["ok"] * 6 + ["low on test strips"])
    next_appointment = (day_date + timedelta(days=random.randint(1, 20))).isoformat()
    diet_followed = random.choice(
        ["followed diet well"] * 4 +
        ["said fine, but mentioned a sweet treat later"]
    )
    food_today = random.choice([
        "oatmeal, salad, grilled chicken",
        "toast, rice and dal, light dinner",
        "eggs, sandwich, soup",
    ])

    tier = classify_tier(blood_sugar, medication_taken, symptoms)

    return {
        "date": day_date.isoformat(),
        "food_today": food_today,
        "blood_sugar": blood_sugar,
        "medication_taken": medication_taken,
        "medication_stock": medication_stock,
        "supplies_status": supplies_status,
        "next_appointment": next_appointment,
        "diet_followed": diet_followed,
        "notes": symptoms,
        "tier": tier,  # included here for the dummy data / chart only -
                        # real log_checkin() entries don't store this, the
                        # agent derives it fresh each time from history
    }


def generate_month(person: str, start_date: date) -> list:
    days = []
    # Plan out 30 days: mostly good, a handful needing attention, and
    # exactly one guaranteed emergency day, placed roughly mid-month.
    forced_tiers = {10: "emergency", 4: "needs_attention",
                    17: "needs_attention", 23: "needs_attention"}

    for i in range(30):
        day_date = start_date + timedelta(days=i)
        forced = forced_tiers.get(i)
        days.append(generate_day(person, day_date, force_tier=forced))

    return days


if __name__ == "__main__":
    start = date.today() - timedelta(days=29)

    for person in ["mom", "dad"]:
        month_data = generate_month(person, start)

        month_path = os.path.join(DATA_DIR, f"{person}_dummy_month.json")
        with open(month_path, "w") as f:
            json.dump(month_data, f, indent=2)

        week_data = month_data[-7:]
        week_path = os.path.join(DATA_DIR, f"{person}_dummy_week.json")
        with open(week_path, "w") as f:
            json.dump(week_data, f, indent=2)

        tier_counts = {}
        for entry in month_data:
            tier_counts[entry["tier"]] = tier_counts.get(entry["tier"], 0) + 1

        print(f"{person}: generated {len(month_data)} days -> {tier_counts}")
        print(f"  saved: {month_path}")
        print(f"  saved: {week_path}")
