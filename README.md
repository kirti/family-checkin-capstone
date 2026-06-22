# Family Check-In Agent

**Track:** Agents for Good
**Course:** Kaggle 5-Day AI Agents Intensive: Vibe Coding (with Google)

## Live demo

- **App**: https://kirti.github.io/family-checkin/
- **Backend health check**: https://family-checkin-backend.onrender.com/api/health

## The problem

I call my parents every day to check on them - they're both managing
diabetes - and a lot gets missed when you're only half-tracking things
in your head. Did Mom miss her evening medication two days running? Is
Dad's blood sugar trending up over a week, not just today? This project
turns that daily routine into an actual agent.

Full design rationale: [`PROJECT.md`](PROJECT.md)

## What's in this repository

This is the **real, working system** - not a simplified demo.

- **`backend/`** - the genuine source behind the live Render deployment:
  Gemini-based agent reasoning, tool use, a deterministic emergency
  layer, session-auth, Postgres storage, Resend email
- **`docs/`** - the genuine source behind the live GitHub Pages site
- **`kaggle-notebook-demo/`** - an earlier, simpler prototype built
  directly as a Kaggle-notebook-style script (local JSON files, no
  deployment needed), showing the core agent concepts in their most
  minimal, directly-runnable form

## Why the agent's role isn't just "code that sends an email"

This is worth being explicit about, since it's the most important design
decision in the project. The system has **two distinct decision paths**:

1. **Emergency detection is deterministic, by design** - fixed blood
   sugar thresholds and symptom keywords, checked in plain Python
   (`emergency.py`), not decided by the LLM. This was a deliberate
   choice: for a decision with real physical safety consequences, a
   fixed, auditable rule is more trustworthy than model judgment that
   could vary between runs. Knowing *when not* to delegate a decision to
   an LLM is itself part of responsible agent design.

2. **Everything else genuinely is agentic reasoning.** For every normal
   day's check-in, Gemini decides what to do with no hardcoded logic
   telling it the answer:
   - It calls `get_history(person)` itself, deciding to look at the
     past before judging today
   - It weighs multiple independent signals (medication adherence,
     blood sugar trend, appointment timing, diet contradictions buried
     in free text) against each other
   - It decides *whether* an alert is warranted at all - most days, it
     correctly decides not to alert, to avoid alert fatigue
   - It decides *who* should be notified based on severity
   - It writes the actual summary text itself, including catching
     details mentioned only in passing (e.g. "felt fine" early in a
     conversation, then a contradicting detail later)

None of that is a template or an if/else tree - it's the model reasoning
over tool outputs and deciding the next action, which is exactly the
agent behavior this course is about. The deterministic safety net exists
*alongside* that reasoning for the one decision where getting it wrong
has the highest cost, not instead of it.

## Architecture

```
Check-in submitted (web form)
        |
        v
Flask backend
        |
        +--> Deterministic emergency check (blood sugar thresholds,
        |     symptom keywords) - bypasses the LLM entirely for the
        |     highest-stakes decision
        |
        +--> If not an emergency: Gemini agent
        |     - get_history(person)  [tool]
        |     - send_alert(...)      [tool, only if warranted]
        |     - returns a plain-language daily summary
        |
        v
Postgres (Neon) - per-person history, used for trend detection
        |
        v
Resend (HTTP email API) - real alerts when something needs attention
```

## Future enhancements

A few concrete next steps, identified but not built yet, in rough order
of effort vs. payoff:

- **Audio input** - the real-world workflow this project is based on is
  a phone call, not a form. A natural next step is letting Mom/Dad
  record a short voice note instead of typing, with Gemini transcribing
  and extracting the structured fields directly from audio (Gemini
  supports audio understanding natively) - this would be a genuinely
  multimodal upgrade tied directly to the actual use case, not just an
  added feature for its own sake.
- **Structured output (`responseSchema`)** - constrain the agent's daily
  summary to a strict JSON shape instead of free text, for more
  reliable downstream use (e.g. directly populating the frontend instead
  of just displaying a paragraph).
- **Built-in Google Search grounding** - mix Gemini's built-in search
  tool with the custom tools already in use, e.g. to offer a general
  (non-prescriptive) diabetes care tip on good days.
- **Multi-recipient email delivery** - currently all alerts go to a
  single verified address (a Resend limitation without a custom domain,
  see above) - verifying a domain would unlock the originally-designed
  multi-recipient escalation (caregiver + a second family member).
- **A second, gentler-toned agent** - rewriting the caregiver-facing
  summary into a softer version for the parent-facing side, as a small
  multi-agent extension.

## Tech stack

Gemini API (function calling), Flask, Postgres (Neon), Resend,
deployed on Render (backend) and GitHub Pages (frontend).
