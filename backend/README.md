# Family Check-In Agent — Backend

The real backend powering the live Family Check-In app: a Gemini-based
agent that reasons about daily health check-ins for two elderly parents,
combined with a deterministic safety layer for true medical emergencies.

This repo is private because it's the operational copy connected to the
live Render deployment. A full public copy of this same code (for review
purposes) lives in the [capstone submission repo].

## What this does

1. Receives a check-in (medication taken, blood sugar, mood, free-text
   notes) from the frontend
2. Runs a **deterministic safety check first** (`emergency.py`) - fixed
   blood sugar thresholds and symptom keywords, checked in plain Python,
   not left to the LLM's judgment, since a missed/wrong call here has
   real consequences
3. If it's not an emergency, hands off to **Gemini** (`agent_logic.py`),
   which calls tools to look at history, decide whether anything needs
   a caregiver alert, and write a plain-language summary
4. Logs everything to Postgres (`db_tools.py`) and sends real email
   alerts via Resend (`email_sender.py`)
5. All of this sits behind simple session-based login auth (`auth.py`),
   enforced on the API itself, not just the frontend page

## Architecture

```
POST /api/checkin
        |
        v
  is_emergency()? -------- yes --> handle_emergency()
        |                              - logs the entry
        no                             - sends urgent email immediately
        |                              - repeats 3x via background thread
        v
  run_checkin() [Gemini]
        |
        +--> get_history(person)   [tool]
        +--> send_alert(...)       [tool, only if warranted]
        |
        v
  Postgres (Neon) + Resend email
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask routes: `/api/login`, `/api/checkin`, `/api/history/<person>`, `/api/health` |
| `auth.py` | Session tokens, rate-limited login, `@require_auth` decorator |
| `emergency.py` | Deterministic emergency detection + repeated escalation |
| `agent_logic.py` | Gemini agent for normal-day reasoning (good day vs. needs attention) |
| `db_tools.py` | Postgres-backed logging, history retrieval, alert sending |
| `email_sender.py` | Resend HTTP API email (not SMTP - see note below) |
| `classify.py` | Labels past entries by tier, for the frontend charts |

## Why email goes through Resend, not SMTP

Render's free tier blocks outbound traffic to SMTP ports (25, 465, 587)
entirely. Resend sends over normal HTTPS, so it isn't affected. One
current limitation: without a verified custom domain, Resend can only
deliver to the single email address the account was created with -
multi-recipient delivery is a documented next step, not implemented yet.

## Environment variables

See `.env.example` for the full list. Required: `DATABASE_URL`,
`GOOGLE_API_KEY`, `RESEND_API_KEY`, `RESEND_VERIFIED_EMAIL`,
`SITE_LOGIN_USERNAME`, `SITE_LOGIN_PASSWORD`, plus `CAREGIVER_EMAIL`,
`FAMILY_EMAIL`, `EMERGENCY_EMAILS`, `DOCTOR_NAME`, `DOCTOR_PHONE` for
the alert content itself.

## Local setup and deployment

See `TEST_LOCALLY.md` and `DEPLOY.md`.
