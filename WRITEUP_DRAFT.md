# Family Check-In Agent

**Track:** Agents for Good
**Live app:** https://kirti.github.io/family-checkin/
**Public codebase:** https://github.com/YOUR-USERNAME/family-checkin-capstone

---

## The problem

I call my parents every day. Partly to track their health — they're
both managing diabetes — and partly just to hear how they're really
doing. A quick structured check-in misses things. In a real
conversation, details come out gradually: "diet's fine" early on, then
later, "oh, I did have some cake earlier." Important patterns are easy
to track for one day but hard to track across weeks — is a missed dose
a one-off, or the start of a streak? Is a blood sugar reading just a bad
moment, or part of a trend?

This project turns that real daily routine into an agent: a check-in
gets logged, reasoned about against history, and escalated only when it
actually matters — including a hard safety net for genuine medical
emergencies, kept deliberately separate from the LLM's day-to-day
judgment.

## What it does

Mom and Dad each have their own simple check-in form (designed for
~70+ users — large tap targets, minimal typing, no logins they have to
remember beyond one shared password). Submitting it:

1. Runs a **deterministic safety check** first — fixed blood sugar
   thresholds (below 70 or above 300 mg/dL) and symptom keywords
   (confusion, fainting, chest pain, etc.), checked in plain Python, not
   left to the model. If triggered: an urgent email fires immediately,
   repeating three times, naming their doctor and recommending emergency
   services — bypassing the agent entirely.
2. If it's not an emergency, hands off to **Gemini**, which:
   - calls a tool to retrieve that person's recent history
   - decides whether anything is alert-worthy (missed medication, an
     elevated/trending blood sugar reading, an upcoming appointment, a
     diet contradiction that's part of a pattern)
   - calls a tool to send a single consolidated alert email if and only
     if something crosses that bar — most days, correctly, nothing fires
   - writes a plain-language summary of the day
3. Everything is logged to a database, building a real history per
   person, visualized as a color-coded trend chart (good / needs
   attention / emergency) that a family member can tap through for the
   exact details of any day.

## Why the agent's role is more than "code that emails you"

This is the design decision I want to be most explicit about, because
it's easy to misread at a glance.

**The emergency path is intentionally not an agent decision.** It's a
fixed rule: if a number crosses a line, send the email — full stop, no
model judgment involved. That's deliberate. For the one decision in
this whole system where being wrong has the highest real-world cost, a
predictable, auditable rule is more trustworthy than asking an LLM to
re-derive the right answer every time. Knowing *when not* to hand a
decision to an LLM is itself part of responsible agent design, not a
shortcut around building one.

**Everywhere else, the reasoning is genuinely the model's.** On a normal
day, nothing tells Gemini what to conclude:
- It chooses to look at history before judging today, by calling a tool
  for it — that's not hardcoded into the request, it's something the
  model decides to do
- It weighs several independent signals against each other (a missed
  dose *and* a rising blood sugar *and* an appointment in two days) to
  reach one combined judgment
- It correctly does nothing on most days — a real judgment call, since
  over-alerting would make the whole system useless
- It catches a detail mentioned only in passing in free text — "felt
  fine," then later, an offhand mention of dessert — which a keyword
  search alone wouldn't reliably catch
- It writes the actual summary in its own words, differently each time

That reasoning loop — tool use, memory via history, multi-step judgment,
deciding when (and when not) to act — is the actual agent work this
course is about. The deterministic safety net sits alongside it for
exactly one high-stakes case, not instead of it.

## Architecture

```
Check-in submitted (web form)
        |
        v
Flask backend
        |
        +--> Deterministic emergency check (blood sugar thresholds,
        |     symptom keywords) -- bypasses the LLM entirely
        |
        +--> If not an emergency: Gemini agent
        |     - get_history(person)  [tool]
        |     - send_alert(...)      [tool, only if warranted]
        |     - returns a plain-language daily summary
        |
        v
Postgres (Neon) -- per-person history, used for trend detection
        |
        v
Resend (HTTP email API) -- real alerts when something needs attention
```

## Tech stack

Gemini API (function calling / tool use), Flask, Postgres (Neon),
Resend, deployed on Render (backend) and GitHub Pages (frontend).
Session-based login auth protects the API itself, not just the
frontend page.

## Real engineering challenges along the way

Worth including honestly, since this was a real build, not a smooth
demo:

- **MongoDB Atlas's login kept failing** (unrelated to this project,
  an account/auth issue) — switched to Postgres on Neon, which
  meant rewriting the storage layer, but the clean separation between
  "tools" and "storage" made that a contained change.
- **Render's free tier blocks outbound SMTP ports entirely** — discovered
  only after deploying, since it fails silently rather than with an
  obvious error. Switched email sending from SMTP to Resend's HTTP API,
  which isn't affected by the block.
- **A subtle correctness bug**: early on, the agent was given control
  over the date field for logging, and it once wrote the literal string
  `"today"` instead of an actual date. Fixed by never letting the LLM
  set anything that needs to be exactly correct and deterministic —
  the date is now always set by the server, not the model.

## Testing

Verified end-to-end with real data across all three tiers:
- A normal day (no alert fires, correctly)
- A day needing attention (missed medication + elevated sugar -> one
  consolidated alert, not three separate ones)
- The same issue recurring (the summary reflects the *pattern*, not just
  that day, because the agent pulled history first)
- A true emergency (blood sugar 40) -> immediate, correctly-formatted,
  repeating urgent email naming the doctor

## Future enhancements

- **Audio input** — since the real workflow is a phone call, letting
  Mom/Dad leave a voice note and having Gemini transcribe + extract
  structured fields directly from audio would be a natural, genuinely
  multimodal next step
- **Structured output** (`responseSchema`) for the daily summary
- **Search grounding** mixed with the existing custom tools, e.g. for
  general (non-prescriptive) care tips on good days
- **Multi-recipient email**, currently limited to one verified address
  without a custom domain
- A second, gentler-toned agent for parent-facing summaries

## Closing note

This started as something I already do every day for people I care
about, and turned into the best demonstration I could build of why
agents are useful: not because they're impressive, but because they can
genuinely catch things a tired, busy person checking in by habit might
miss — while staying out of the way on the one decision where a fixed
rule serves better than a fresh judgment call every time.
