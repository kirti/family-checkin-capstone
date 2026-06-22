"""
test_log_checkin.py

Standalone test for log_checkin(). No Gemini, no agent — just proving this
one tool works correctly by itself before we connect anything to it.

Run with: python tests/test_log_checkin.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools import log_checkin

# Simulate one fake call with Mom
entry = log_checkin(
    person="Mom",
    food_today="oatmeal for breakfast, chicken salad for lunch",
    blood_sugar="145",
    medication_taken="took morning dose, missed evening dose",
    medication_stock="low, about 3 days left",
    supplies_status="ok",
    next_appointment="2026-06-25",
    diet_followed="said it was fine, but mentioned having cake later",
    notes="Sounded a little tired today but in good spirits overall.",
    check_date="2026-06-18",
)

print("Saved entry:")
print(entry)
