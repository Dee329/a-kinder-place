# A Kinder Place

Dee's anonymous, kind-only advice community.

- **Anonymous only:** no accounts, no logins, no real names, no profile pictures, no image uploads (text only), no private messages. Each visitor gets a made-up name like "Warm River 221" stored only in their browser session.
- **Ask and give advice** by topic: Grief, Parenting, Relationships, Money, Work, Health, Everyday life. Replies can be marked Helpful. The feed can be filtered by topic.
- **Kindness moderation:** rude/insulting words, profanity, and all-caps shouting are blocked before a post or reply publishes, with a gentle "say it a kinder way" message.
- **Content rule:** hardcore/explicit sexual questions and nasty/rude sexual posts are blocked. Medical-type questions (health worries, coping, what helped others) are allowed, with a clear note that this is peer advice, not professional medical advice.
- **Report:** every post and reply has a Report button that hides it immediately pending review.
- **Safety:** a crisis-help card is on every page — US: call/text 988, text HOME to 741741. This is peer advice only, not professional medical, legal, or crisis help.
- **Design:** purple, warm, mobile-friendly.

## Run it locally

```bash
cd a-kinder-place
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in a browser.

The SQLite database file `kinder.db` is created automatically on first run, with 4 clearly labeled sample posts. Delete `kinder.db` and restart if you ever want a clean start (the samples will be recreated).

## Deploy for free — Render (recommended first)

Render's free web service tier is the simplest path. No paid service is required.

1. Put this folder in a GitHub repository (create a repo, upload these files).
2. Go to https://render.com → New → Web Service → connect that repository.
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance type:** Free
4. Click Create Web Service. Render gives you a public URL like `https://a-kinder-place.onrender.com`.
5. Open that URL on your phone and test: post a kind question, try a rude one (it should be blocked), and check the topic filter.

Notes on the free tier:
- Free Render services sleep after inactivity, so the first visit after a pause can take ~30–60 seconds to wake up. That is normal on the free tier.
- **Important — data persistence:** on Render's free tier, the local SQLite file (`kinder.db`) can be reset when the service restarts or redeploys, because free instances do not keep a permanent disk by default. For a small community launch this is acceptable, but before growing large, add a Render persistent disk (paid) or move the database to a hosted Postgres database (Render offers a free Postgres tier at times — check its current pricing before relying on it). The app code itself does not need to change for a first launch; this is a hosting choice, not a rebuild.
- Set a `SECRET_KEY` environment variable in Render (Environment → Add Environment Variable) to a long random string. Without it, the app falls back to a development key, which is fine for testing but should not be used for a real public launch.
- Reviewing reported posts: reported items are hidden (`hidden = 1`) in the database. A host reviews them by checking the database directly — there is deliberately no public "unhide" button, so visitors cannot restore their own reported posts.

## Alternative free hosting

- **Railway:** create a project from the same GitHub repo, set the start command to `gunicorn app:app`. Railway's free trial/credits change over time, so check its current free offer before choosing it.
- **PythonAnywhere (free tier):** upload the files, create a Flask web app pointing at `app.py`, and install the requirements in its console. The free tier uses a `yourname.pythonanywhere.com` address.

## Files

- `app.py` — the whole server: routes, moderation filter, database schema, sample posts.
- `templates/index.html` — the page: ask form, house rules, crisis card, topic filter, feed, replies, Helpful and Report buttons.
- `static/style.css` — purple, mobile-friendly styling.
- `requirements.txt` — Flask + gunicorn.
- `Procfile` — `web: gunicorn app:app` (used by some hosts; Render uses the Start Command above).

## What this package is — and is not

This is a complete, deployable package ready for hosting. It is **not yet live on the public internet** until you follow the deployment steps above and Render (or another host) gives you a URL. Once you have that URL, share it — that is the moment A Kinder Place goes live.
