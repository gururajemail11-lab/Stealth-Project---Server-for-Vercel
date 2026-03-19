"""
receiver.py
────────────
Lightweight Flask API running on your central server.
GitHub Actions workers POST their scraped jobs here.
Also triggers Telegram alerts for matching jobs.
"""

import logging
import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from config import CONFIG
from database import init_db, bulk_insert_jobs, get_unalerted_jobs, mark_alerted, get_stats, search_jobs
from alerts import send_telegram_alert, filter_matching_jobs

# Windows console often uses cp1252; use UTF-8 so emojis/Unicode don't cause UnicodeEncodeError
def _utf8_stream_handler():
    if hasattr(sys.stdout, "buffer"):
        return logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace"))
    return logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_utf8_stream_handler()]
)
log = logging.getLogger(__name__)


def _validate_runtime_config():
    # Fail fast if secrets are not configured in Vercel/local environment.
    db_url = CONFIG.get("neon_database_url", "")
    if not db_url or "USER:PASSWORD@HOST/DBNAME" in db_url:
        raise RuntimeError("NEON_DATABASE_URL is missing or still using placeholder value")
    secret = CONFIG.get("receiver_secret", "")
    if not secret or secret == "CHANGE_ME_TO_A_LONG_RANDOM_SECRET":
        raise RuntimeError("RECEIVER_SECRET is missing or still using placeholder value")


_validate_runtime_config()
app = Flask(__name__)
init_db(CONFIG["neon_database_url"])


@app.route("/receive", methods=["POST"])
@app.route("/api/receive", methods=["POST"])
def receive():
    """Endpoint that GitHub Actions workers POST results to."""
    try:
        data = request.get_json(force=True)

        # Auth check
        if data.get("secret") != CONFIG["receiver_secret"]:
            log.warning(f"❌ Invalid secret from {request.remote_addr}")
            return jsonify({"error": "unauthorized"}), 401

        jobs        = data.get("jobs", [])
        keyword     = data.get("keyword", "")
        github_user = data.get("github_user", "unknown")

        if not jobs:
            return jsonify({"status": "ok", "new": 0, "message": "empty payload"})

        # Save to DB
        stats = bulk_insert_jobs(CONFIG["neon_database_url"], jobs, keyword, github_user)

        # Alert for matching jobs
        if stats["new"] > 0:
            unalerted = get_unalerted_jobs(CONFIG["neon_database_url"])
            matching  = filter_matching_jobs(unalerted, CONFIG["alert_keywords"])
            if matching:
                sent = send_telegram_alert(matching, CONFIG)
                if sent:
                    mark_alerted(CONFIG["neon_database_url"], [j["id"] for j in matching])
                    log.info(f"📲 Alerted {len(matching)} matching jobs via Telegram")
            # Mark non-matching as alerted too (so we don't re-process)
            non_matching_ids = [j["id"] for j in unalerted if j not in matching]
            if non_matching_ids:
                mark_alerted(CONFIG["neon_database_url"], non_matching_ids)

        log.info(f"📥 Received from [{github_user}]: {stats}")
        return jsonify({"status": "ok", **stats})

    except Exception as e:
        log.exception(f"Receiver error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/stats", methods=["GET"])
@app.route("/api/stats", methods=["GET"])
def stats():
    """Quick health check + stats."""
    s = get_stats(CONFIG["neon_database_url"])
    return jsonify(s)


@app.route("/search", methods=["GET"])
@app.route("/api/search", methods=["GET"])
def search():
    """Search saved jobs."""
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 50))
    if not query:
        return jsonify({"error": "provide ?q=keyword"}), 400
    jobs = search_jobs(CONFIG["neon_database_url"], query, limit=limit)
    return jsonify({"count": len(jobs), "jobs": jobs})


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
def index():
    s = get_stats(CONFIG["neon_database_url"])
    return f"""
    <h2>LinkedIn Hunter - Neon Receiver</h2>
    <pre>
Total jobs   : {s['total_jobs']:,}
Last 24h     : {s['last_24h']:,}
Unalerted    : {s['unalerted']}
Total runs   : {s['total_runs']:,}
    </pre>
    <p><a href="/stats">/stats (JSON)</a> | <a href="/search?q=python">/search?q=python</a></p>
    """


if __name__ == "__main__":
    port = CONFIG["receiver_port"]
    log.info(f"🌐 Receiver starting on port {port}")
    app.run(host=CONFIG["receiver_host"], port=port, debug=False)
