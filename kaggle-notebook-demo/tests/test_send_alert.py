"""
test_send_alert.py

Standalone test for send_alert(). No Gemini, no agent — just confirming
the alert prints clearly and logs correctly before we connect anything to it.

Run with: python tests/test_send_alert.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools import send_alert

alert = send_alert(
    person="Mom",
    message=(
        "Mom missed her evening medication two days in a row "
        "(2026-06-18 and 2026-06-19), and her medication stock is low. "
        "Blood sugar also rose from 145 to 160 over the same period."
    ),
    recipients=["me", "sister"],
    reason="missed medication + rising blood sugar",
)

print()
print("Returned alert record:")
print(alert)
