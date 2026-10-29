"""
A Kinder Place — Dee's anonymous, kind-only advice community.
Text only. No accounts, no real names, no profile pictures,
no image uploads, no private messages.

Run locally:  python app.py
Deploy:       see README.md (Render free tier, gunicorn)
"""
import os
import random
import re
import sqlite3
from datetime import datetime

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
import json as _json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "a-kinder-place-dev-only-change-me")
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kinder.db")

TOPICS = ["Grief", "Parenting", "Relationships", "Money", "Work", "Health", "Everyday life"]

ADJECTIVES = ["Warm", "Gentle", "Kind", "Quiet", "Bright", "Soft", "Calm", "Hopeful", "Patient", "Caring"]
NOUNS = ["River", "Willow", "Meadow", "Sunrise", "Harbor", "Garden", "Lantern", "Feather", "Brook", "Compass"]

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")

def send_reply_push(post_id):
    """Ping browsers that asked to be notified about replies to post_id.
    No names, emails or phone numbers are used - only a browser push
    subscription the visitor opted into. Failures (expired subscriptions)
    are removed silently. Push is skipped if VAPID keys are not set."""
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        return
    try:
        from pywebpush import WebPushException, webpush
    except Exception:
        return
    db = get_db()
    subs = db.execute("SELECT * FROM push_subscriptions WHERE post_id = ?", (post_id,)).fetchall()
    for sub in subs:
        try:
            webpush(
                subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                data="Someone replied to your question on A Kinder Place. Come back and read their kind advice.",
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:dee@a-kinder-place.example"},
            )
        except Exception:
            try:
                db.execute("DELETE FROM push_subscriptions WHERE id = ?", (sub["id"],))
                db.commit()
            except Exception:
                pass

# Words that are rude / insulting. Matched as whole words (or phrases).
RUDE_WORDS = [
    "idiot", "stupid", "dumb", "moron", "loser", "hate you", "shut up",
    "ugly", "worthless", "pathetic", "disgusting person", "get lost",
    "damn you", "hell with you",
]
# Profanity placeholders kept generic: block common swear roots.
PROFANITY_ROOTS = ["fuck", "shit", "bitch", "bastard", "asshole", "dickhead"]

# Hardcore / explicit sexual content. Deliberately a phrase list, NOT the
# word "sex" on its own, so genuine medical/health questions can pass.
# e.g. "losing desire after grief" or "worried about my health" must pass.
EXPLICIT_SEXUAL = [
    "porn", "pornography", "erotic", "horny", "sexting", "sex toy",
    "nude pictures", "naked pictures", "send nudes", "hook up for sex",
    "explicit pictures", "onlyfans", "cam girl", "cam show",
    "sex video", "sex chat", "dirty talk", "kinky sex",
]

def new_alias():
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.randint(100, 999)}"

def get_alias():
    if "alias" not in session:
        session["alias"] = new_alias()
    return session["alias"]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            body TEXT NOT NULL,
            alias TEXT NOT NULL,
            created_at TEXT NOT NULL,
            helpful_count INTEGER NOT NULL DEFAULT 0,
            hidden INTEGER NOT NULL DEFAULT 0,
            is_sample INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL REFERENCES posts(id),
            body TEXT NOT NULL,
            alias TEXT NOT NULL,
            created_at TEXT NOT NULL,
            helpful_count INTEGER NOT NULL DEFAULT 0,
            hidden INTEGER NOT NULL DEFAULT 0
        );
    """)
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    if count == 0:
        now = datetime.utcnow().isoformat(timespec="seconds")
        samples = [
            ("Grief", "It has been a few months since I lost someone I loved, and everyone else seems to have moved on. How do you keep going on the hard days?", "Warm River 221"),
            ("Parenting", "My teenager barely talks to me lately. What is one gentle way to keep the door open without pushing?", "Gentle Willow 304"),
            ("Money", "I am trying to save a little each week on a tight budget. What is one small habit that actually helped you?", "Calm Harbor 118"),
            ("Health", "I have been feeling anxious and not sleeping well. What helps you calm down at night? I know this is peer advice, not medical advice.", "Quiet Meadow 442"),
        ]
        for topic, body, alias in samples:
            db.execute(
                "INSERT INTO posts (topic, body, alias, created_at, is_sample) VALUES (?, ?, ?, ?, 1)",
                (topic, body, alias, now),
            )
        db.commit()

def moderation_check(text):
    """Return an error message if text must be blocked, else None."""
    if not text or not text.strip():
        return "Please write something first."
    lowered = text.lower()
    # All-caps shouting: mostly capital letters, reasonably long.
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) >= 15 and sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.7:
        return "That looks like shouting in all caps. Could you say it a kinder, calmer way?"
    for phrase in EXPLICIT_SEXUAL:
        if phrase in lowered:
            return ("This space does not allow hardcore or explicit sexual posts. "
                    "Could you reword it, or ask a different question? "
                    "Medical and health questions are welcome here.")
    for word in RUDE_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", lowered):
            return "That wording sounds unkind. Could you say it a kinder way?"
    for root in PROFANITY_ROOTS:
        if re.search(r"\b" + root, lowered):
            return "That wording sounds unkind. Could you say it a kinder way?"
    return None

@app.route("/")
def index():
    init_db()
    topic = request.args.get("topic", "")
    db = get_db()
    if topic in TOPICS:
        posts = db.execute(
            "SELECT * FROM posts WHERE hidden = 0 AND topic = ? ORDER BY id DESC", (topic,)
        ).fetchall()
    else:
        topic = ""
        posts = db.execute("SELECT * FROM posts WHERE hidden = 0 ORDER BY id DESC").fetchall()
    result = []
    for post in posts:
        replies = db.execute(
            "SELECT * FROM replies WHERE post_id = ? AND hidden = 0 ORDER BY id ASC", (post["id"],)
        ).fetchall()
        result.append((post, replies))
    return render_template(
        "index.html", topics=TOPICS, selected_topic=topic,
        posts=result, alias=get_alias(), vapid_public_key=VAPID_PUBLIC_KEY,
        error=request.args.get("error", ""), notice=request.args.get("notice", ""),
    )

@app.route("/ask", methods=["POST"])
def ask():
    init_db()
    topic = request.form.get("topic", "")
    body = request.form.get("body", "").strip()
    if topic not in TOPICS:
        return redirect(url_for("index", error="Please choose a topic."))
    error = moderation_check(body)
    if error:
        return redirect(url_for("index", error=error))
    db = get_db()
    db.execute(
        "INSERT INTO posts (topic, body, alias, created_at) VALUES (?, ?, ?, ?)",
        (topic, body, get_alias(), datetime.utcnow().isoformat(timespec="seconds")),
    )
    db.commit()
    return redirect(url_for("index", notice="Your question was posted. Thank you for asking kindly."))

@app.route("/reply/<int:post_id>", methods=["POST"])
def reply(post_id):
    init_db()
    body = request.form.get("body", "").strip()
    error = moderation_check(body)
    if error:
        return redirect(url_for("index", error=error))
    db = get_db()
    post = db.execute("SELECT id FROM posts WHERE id = ? AND hidden = 0", (post_id,)).fetchone()
    if post is None:
        return redirect(url_for("index", error="That question is no longer available."))
    db.execute(
        "INSERT INTO replies (post_id, body, alias, created_at) VALUES (?, ?, ?, ?)",
        (post_id, body, get_alias(), datetime.utcnow().isoformat(timespec="seconds")),
    )
    db.commit()
    send_reply_push(post_id)
    return redirect(url_for("index", notice="Thank you — your advice was posted."))

@app.route("/push/subscribe", methods=["POST"])
def push_subscribe():
    init_db()
    try:
        data = request.get_json(force=True) or {}
        post_id = int(data.get("post_id", 0))
        sub = data.get("subscription") or {}
        endpoint = sub.get("endpoint", "")
        keys = sub.get("keys") or {}
        if not post_id or not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            return jsonify({"ok": False}), 400
        db = get_db()
        db.execute("DELETE FROM push_subscriptions WHERE post_id = ? AND endpoint = ?", (post_id, endpoint))
        db.execute(
            "INSERT INTO push_subscriptions (post_id, endpoint, p256dh, auth, created_at) VALUES (?, ?, ?, ?, ?)",
            (post_id, endpoint, keys["p256dh"], keys["auth"], datetime.utcnow().isoformat(timespec="seconds")),
        )
        db.commit()
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"ok": False}), 400

@app.route("/helpful/<kind>/<int:item_id>", methods=["POST"])
def helpful(kind, item_id):
    init_db()
    db = get_db()
    table = "posts" if kind == "post" else "replies" if kind == "reply" else None
    if table is None:
        return redirect(url_for("index"))
    db.execute(f"UPDATE {table} SET helpful_count = helpful_count + 1 WHERE id = ?", (item_id,))
    db.commit()
    return redirect(url_for("index"))

@app.route("/report/<kind>/<int:item_id>", methods=["POST"])
def report(kind, item_id):
    init_db()
    db = get_db()
    table = "posts" if kind == "post" else "replies" if kind == "reply" else None
    if table is None:
        return redirect(url_for("index"))
    # Hide immediately pending review. There is no un-hide route in the
    # public app on purpose: a host reviews the SQLite database directly.
    db.execute(f"UPDATE {table} SET hidden = 1 WHERE id = ?", (item_id,))
    db.commit()
    return redirect(url_for("index", notice="Thank you. That post has been hidden while it is reviewed."))

if __name__ == "__main__":
    with app.app_context():
        init_db()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
