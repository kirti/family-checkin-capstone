# Backend deployment guide

## 1. Neon (free Postgres database)

We switched from MongoDB Atlas to Neon after running into repeated
login/auth issues with Atlas's web console. Neon is a different company
with a different sign-up flow, so that specific problem shouldn't follow
us here.

1. Go to https://neon.tech and sign up (GitHub or Google sign-in, no
   credit card needed for the free tier)
2. Create a new project (it'll prompt you through this on signup) -
   name it something like "family-checkin"
3. On the project dashboard, find the **Connection string** (usually
   shown right away, or under "Connection Details") - it looks like:
   `postgresql://username:password@ep-xxxxx.region.aws.neon.tech/dbname?sslmode=require`
4. Copy that whole string - this is your `DATABASE_URL`

That's it - no separate "network access" step like Atlas required, no
database user setup needed (Neon creates one for you automatically).

## 2. Render.com (free backend hosting)

1. Push this whole project to a GitHub repo (if you haven't already)
2. Go to https://render.com and sign up (free, no card required for this tier)
3. Click **New -> Web Service**, connect your GitHub repo
4. Settings:
   - **Root directory**: `backend`
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app`
5. Under **Environment**, add these variables:
   - `DATABASE_URL` = (the connection string from step 1.3-1.4)
   - `GOOGLE_API_KEY` = (your Gemini API key)
   - `GMAIL_ADDRESS` = `your-gmail-address@gmail.com`
   - `GMAIL_APP_PASSWORD` = (your Gmail app password)
   - `EMERGENCY_REPEAT_INTERVAL_SECONDS` = `300` (or a short number like
     `10` if you're testing/recording a demo)
6. Click **Deploy**. Once it's live, Render gives you a URL like
   `https://your-app-name.onrender.com`

The app automatically creates its database tables the first time it
starts up (`init_db()` runs at startup) - no manual table creation needed.

## 3. Connect the frontend to the backend

In `docs/mom-checkin.html` and `docs/dad-checkin.html`:
```js
const ENDPOINT_URL = "https://your-app-name.onrender.com/api/checkin";
```

In `docs/mom-history.html` and `docs/dad-history.html`:
```js
const API_BASE = "https://your-app-name.onrender.com";
```

## 4. Test it

1. Visit `/api/health` on your Render URL - should show `{"status": "ok"}`
2. Open a check-in form, fill it in, submit
3. In the Neon dashboard, use the **SQL Editor** to run
   `SELECT * FROM checkins;` - you should see your new row
4. If your test numbers should trigger an alert or emergency, check email

## Checking your data directly in Neon (anytime)

1. Go to https://console.neon.tech and open your project
2. Click **"SQL Editor"** in the left sidebar
3. See every check-in, newest first:
   ```sql
   SELECT * FROM checkins ORDER BY id DESC;
   ```
4. See every alert that was sent:
   ```sql
   SELECT * FROM alerts ORDER BY id DESC;
   ```
5. Delete a bad test row (e.g. one with `date = 'today'`, from before a
   bug fix where the date was sometimes stored wrong):
   ```sql
   DELETE FROM checkins WHERE date = 'today';
   ```

## Note on Render's free tier

Render's free web services "sleep" after periods of inactivity and take
~30-60 seconds to wake up on the next request - fine for personal use,
just don't mistake a slow first response for a bug.
