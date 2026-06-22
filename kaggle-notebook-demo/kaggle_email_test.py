# Standalone test: just the email sending, nothing else.
# If Kaggle blocks outbound SMTP, this will fail with a clear timeout
# error in about 10 seconds, instead of hanging forever.

import smtplib
from email.mime.text import MIMEText
from kaggle_secrets import UserSecretsClient

user_secrets = UserSecretsClient()
GMAIL_ADDRESS = user_secrets.get_secret("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = user_secrets.get_secret("GMAIL_APP_PASSWORD")

to_address = "your-email@example.com"

msg = MIMEText("This is a test email from the Family Check-In Agent.")
msg["Subject"] = "Test email - ignore"
msg["From"] = GMAIL_ADDRESS
msg["To"] = to_address

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [to_address], msg.as_string())
    print("Email sent successfully.")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
