# Testing the backend locally

## 1. Set up Neon first (still needed even for local testing)

Local testing still needs a real database to write to. Follow section 1
of DEPLOY.md to get your `DATABASE_URL` connection string from Neon -
it works the same way whether your code is running locally or on Render.

(If you'd rather not sign up for anything right now, Postgres can also
run entirely on your own machine with no account at all:
`brew install postgresql@16`, then `DATABASE_URL=postgresql://localhost/postgres`.
Either way works with the exact same code.)

## 2. Set up a local .env file

In the `backend/` folder, create a `.env` file (copy `.env.example`)
with your real values:
```
DATABASE_URL=postgresql://...
GOOGLE_API_KEY=...
GMAIL_ADDRESS=xxxx@gmail.com
GMAIL_APP_PASSWORD=...
EMERGENCY_REPEAT_INTERVAL_SECONDS=10
```
(Using `10` seconds here instead of `300` so emergency testing doesn't
take 15 real minutes.)

## 3. Install dependencies and run

```
cd backend
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt python-dotenv
```

Flask doesn't load `.env` automatically - add these two lines at the very
top of `app.py` (above the other imports) for local testing only:
```python
from dotenv import load_dotenv
load_dotenv()
```

Then run:
```
python3 app.py
```

You should see Flask start up, and a line confirming it's running on
`http://0.0.0.0:5000`. If the database connects successfully, there
should be NO "Warning: could not initialize database" line - if you see
that warning, double check your `DATABASE_URL`.

## 4. Test the health check

```
curl http://localhost:5000/api/health
```
Should return `{"status": "ok"}`.

## 5. Test a check-in directly (without the HTML form yet)

```
curl -X POST http://localhost:5000/api/checkin \
  -H "Content-Type: application/json" \
  -d '{"person":"Mom","medication_taken":"Missed it today","blood_sugar":"200","feeling":"Tired","notes":"had some cake earlier"}'
```

Expected: a JSON response with a `tier` and `message`, and (since this
example has a missed dose + elevated sugar) a real email too.

## 6. Test the HTML forms against localhost

In `docs/mom-checkin.html`, temporarily set:
```js
const ENDPOINT_URL = "http://localhost:5000/api/checkin";
```
Then open the HTML file directly in a browser and submit it for real.

## 7. Test history

```
curl http://localhost:5000/api/history/Mom?range=week
```
Should return the entries logged so far, each with a `tier` field.

## Remember to switch back

Once everything works locally, swap `ENDPOINT_URL`/`API_BASE` back to
the real Render URL before deploying, and remove the two `dotenv` lines
from `app.py` (Render sets environment variables itself).
