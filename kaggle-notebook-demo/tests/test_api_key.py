"""
test_api_key.py

Smallest possible check that the Gemini API key works at all, before we
build anything more complex on top of it.

Run with: python tests/test_api_key.py
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Reply with exactly: API key works.",
)

print(response.text)
