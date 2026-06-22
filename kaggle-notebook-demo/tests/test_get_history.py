"""
test_get_history.py

Standalone test for get_history(). No Gemini, no agent — just confirming
this tool correctly retrieves past entries before we connect anything to it.

Run with: python tests/test_get_history.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools import log_checkin, get_history

# Add a second day for Mom, on top of the entry from test_log_checkin.py,
# so we have an actual pattern to look at: medication missed two days running.
log_checkin(
    person="Mom",
    food_today="toast and eggs, then had some cookies in the afternoon",
    blood_sugar="160",
    medication_taken="missed evening dose again",
    medication_stock="still low, needs refill soon",
    supplies_status="ok",
    next_appointment="2026-06-25",
    diet_followed="said she's been good, then mentioned the cookies",
    notes="A bit more tired than usual, but cheerful on the phone.",
    check_date="2026-06-19",
)

print("Full history for Mom:")
for day in get_history("Mom"):
    print(f"  {day['date']}: meds = {day['medication_taken']!r}, "
          f"sugar = {day['blood_sugar']}")

print()
print("Last 1 entry only:")
print(get_history("Mom", last_n=1))

print()
print("History for someone with no data yet (Dad):")
print(get_history("Dad"))
