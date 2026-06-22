# Family Check-In Agent

**Track:** Agents for Good
**Course:** Kaggle 5-Day AI Agents Intensive: Vibe Coding (with Google)

## The problem

I call my parents every day — partly to track their health, partly just to
hear how they're really doing. A quick structured check-in misses things:
in a 10–15 minute call, details come out gradually that wouldn't show up if
you only asked direct questions ("diet's fine" early on, then later "oh, I
did have some sweets earlier"). Important things — missed medication,
low supply stock, an upcoming appointment, an abnormal blood sugar reading —
are easy to track for one day, but hard to track as a *pattern* across weeks,
especially when juggling this for more than one parent.

This is a real, current task I do myself.

## What gets tracked each call

Structured info (asked directly):
- Food eaten today
- Blood sugar level
- Medication taken on time? (yes/no)
- Medication stock — enough, or needs refill?
- Next doctor's appointment (date)
- Medical supplies (e.g. test strips) — enough, or running low?
- Following recommended diet?

Unstructured info (often surfaces later in the conversation, not in direct
answers):
- Mood / how they're "really" doing
- Off-hand mentions that contradict an earlier answer (e.g. said diet was
  fine, later mentioned a non-diet food)
- Anything else they bring up unprompted

## What the agent does

1. Takes today's call notes (typed in after the call, or eventually a call
   transcript) — both the structured answers and the free-form parts
2. Extracts the structured fields, **and** scans the free-form notes for
   details that update or contradict the structured answers
3. Pulls that person's history to check for patterns (e.g. missed meds
   2 days running; blood sugar trending up; appointment is in 3 days)
4. Decides what's "normal" vs. "alert-worthy" using clear rules:
   - Abnormal blood sugar reading → alert
   - Medication missed → alert
   - Medication or supplies running low → alert
   - Appointment within N days → reminder
   - Diet contradiction (said fine, but wasn't) → flagged, lower urgency
5. Logs the full entry (structured + notes) to that person's history
6. Sends an alert to me (primary caregiver), and optionally a second
   family member, only when something actually needs attention — not
   every day

## Why this fits the course concepts

- **Tool use / function calling**: log_checkin(), get_history(), send_alert()
- **Reasoning over unstructured + structured input**: the agent has to
  combine direct answers with details buried in free text — not simple
  keyword matching
- **Short-term memory**: today's call notes
- **Long-term memory**: per-person rolling history, used to detect trends
  (blood sugar drift, repeated missed meds) not just single-day issues
- **Personalization**: separate history/baseline per parent
- **Decision logic / alerting**: agent decides *when* to alert, and *who*,
  based on severity — avoids alert fatigue

## Architecture (high level)

```
Call notes input ("Mom: ate normal breakfast, sugar 145, took morning meds,
                   low on test strips, mentioned having cake later")
        │
        ▼
   Agent (Gemini, function-calling)
        │
        ├──► Tool: get_history(person)         # past entries, for trends
        ├──► Tool: log_checkin(person, entry)   # save today's structured
        │                                         + free-form entry
        ├──► Tool: send_alert(person, message,  # only if something
        │            recipients)                  needs attention
        │
        ▼
   Agent reasons over history + today's entry, produces:
     - Daily summary (always)
     - Alerts, if any, with clear reason + recipient(s)
```

## Deployment extension: self-fill check-in (Mom/Dad use directly)

In addition to the rich call-based check-in (you, after talking to them),
adding a lightweight self-fill form for days they check in themselves.

**Fields (kept deliberately minimal for elderly usability — mostly tap,
not type):**
1. Did you take your medication today? (Yes, all of it / Missed one dose /
   Missed it today)
2. Blood sugar reading (number)
3. How are you feeling? (Good / Tired / Not great / Other + optional text)
4. Anything else you want to mention? (optional free text)

**Architecture (revised again — MongoDB Atlas replaced with Neon/Postgres
after persistent login issues with Atlas's web console; everything else
unchanged thanks to the db_tools.py separation layer):**
- GitHub Pages: landing page + 2 custom elderly-friendly check-in forms
- Backend: Python (Flask), deployed free on Render.com
- Database: **Neon (Postgres, free tier)** — `backend/db_tools.py`
- Emergency detection: deterministic Python thresholds — `backend/emergency.py`
- Normal-day reasoning: Gemini + tools — `backend/agent_logic.py`
- Email: Gmail SMTP, unchanged

**Build order:**
1. [x] GitHub Pages landing page
2. [x] Custom elderly-friendly forms (Mom/Dad), replacing Google Forms
3. [x] Backend skeleton (Flask, 3 endpoints) — verified imports + routes
4. [x] MongoDB-backed tools — `db_tools.py`
5. [x] Deterministic emergency logic — `emergency.py`, tested standalone
6. [ ] You: create MongoDB Atlas free cluster, get connection string
7. [ ] You: deploy backend/ to Render.com with env vars
8. [ ] Update form HTML files' ENDPOINT_URL to the real Render URL
9. [x] Chart/history pages on the frontend (mom-history.html,
       dad-history.html), with week/month toggle, linked from the
       landing page and each check-in's thank-you screen
10. [ ] End-to-end test: submit each form, confirm DB write + correct
       tier + email if warranted

## Status log
- [x] Problem defined (real, personal, detailed use case)
- [x] Tool 1/3 built and tested: `log_checkin()` — saves one day's
      structured + free-form check-in to `data/<person>.json`
- [x] Tool 2/3 built and tested: `get_history()` — retrieves a person's
      past entries (optionally limited to the most recent N), used to
      spot patterns over time
- [x] Tool 3/3 built and tested: `send_alert()` — simulated (prints +
      logs the alert); can be swapped for real Gmail sending later
- [x] Agent loop wired to Gemini — `agent/agent.py`, using automatic
      function calling with the 3 tools + a clear alert policy
      (built and SDK-verified here; live Gemini call needs to be run by
      you, since this sandbox can't reach Gemini's API — see README.md)
- [x] Agent loop wired to Gemini and **verified working** (Kaggle notebook,
      gemini-2.5-flash) — correctly called get_history -> log_checkin ->
      send_alert (x3), caught a diet detail mentioned later in the call,
      and differentiated alert recipients by severity
- [x] Memory persistence — confirmed via get_history/log_checkin
      (per-person JSON files persist across runs)
- [x] Real email alerts confirmed working (Gmail SMTP) — verified actual
      email received for the "medication missed + out of stock" scenario
- [ ] End-to-end demo: confirm pattern-detection (Day 2) and quiet-day
      (no false alert) scenarios with real email too
- [x] Weekly/monthly dummy data generated for Mom and Dad (30 days each,
      all 3 tiers represented) — `agent/generate_dummy_data.py`,
      `data/*_dummy_month.json`, `data/*_dummy_week.json`
- [x] Trend visualization built (blood sugar over time, color-coded by
      tier, toggle between person/period)
- [ ] Writeup + video
