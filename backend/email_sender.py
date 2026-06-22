"""
email_sender.py

Sends email via Resend's HTTP API instead of SMTP. This exists because
Render's free tier blocks outbound traffic to SMTP ports (25, 465, 587)
entirely at the network level - confirmed via Render's own changelog.
Since Resend sends over normal HTTPS, it isn't affected by that block.

IMPORTANT LIMITATION: without verifying a custom domain with Resend, you
can only send to the email address you signed up to Resend with - not to
arbitrary other addresses. For this project, that means every alert
currently goes to RESEND_VERIFIED_EMAIL regardless of who the "intended"
recipient was. Multi-recipient delivery (e.g. a second family member at
a different address) requires owning and verifying a domain - noted as
a planned future enhancement rather than implemented here.
"""

import os
import requests


def send_email(subject: str, body: str) -> dict:
    """
    Send one email via Resend. Always sends to RESEND_VERIFIED_EMAIL
    (see module docstring for why) - the `to` address isn't a parameter
    here on purpose, to avoid silently trying to send somewhere that
    will fail without domain verification.
    """
    api_key = os.environ["RESEND_API_KEY"]
    verified_email = os.environ["RESEND_VERIFIED_EMAIL"]

    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": "onboarding@resend.dev",
            "to": [verified_email],
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
