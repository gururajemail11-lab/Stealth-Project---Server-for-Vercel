"""
alerts.py
──────────
Sends Telegram alerts for matching jobs.
"""

import logging
import requests

log = logging.getLogger(__name__)


def filter_matching_jobs(jobs: list[dict], keywords: list[str]) -> list[dict]:
    """Return jobs whose title/description matches any alert keyword."""
    kws = [k.lower() for k in keywords]
    matched = []
    for job in jobs:
        text = (
            f"{job.get('job_title','')} {job.get('job_description','')} "
            f"{job.get('company_name','')} {job.get('required_skills','')}"
        ).lower()
        if any(kw in text for kw in kws):
            matched.append(job)
    return matched


def send_telegram_alert(jobs: list[dict], config: dict) -> bool:
    """
    Send a Telegram message with the matched jobs.
    Batches into groups of 10 to avoid message length limits.
    """
    token   = config["telegram_token"]
    chat_id = config["telegram_chat_id"]

    if not token or token == "YOUR_BOT_TOKEN":
        log.warning("Telegram not configured, skipping alerts.")
        return False

    # Build message (use DB field names: job_title, company_name, job_url, posted_date)
    def make_message(batch):
        lines = [f"🔔 *{len(batch)} New Matching Jobs Found!*\n"]
        for job in batch:
            title   = job.get("job_title", "N/A")
            company = job.get("company_name", "N/A")
            loc     = job.get("company_hq") or job.get("work_mode") or "—"
            url     = job.get("job_url", "")
            posted  = job.get("posted_date") or job.get("posted_datetime_raw", "")
            lines.append(
                f"━━━━━━━━━━━━━━━\n"
                f"💼 *{title}*\n"
                f"🏢 {company}\n"
                f"📍 {loc}\n"
                f"⏰ {posted}\n"
                f"🔗 [Apply]({url})\n"
            )
        return "\n".join(lines)

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Send in batches of 10
    batch_size = 10
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i+batch_size]
        msg   = make_message(batch)
        try:
            r = requests.post(url, json={
                "chat_id":    chat_id,
                "text":       msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }, timeout=10)
            if r.status_code == 200:
                log.info(f"📲 Telegram batch {i//batch_size + 1} sent ({len(batch)} jobs)")
            else:
                log.error(f"Telegram error: {r.status_code} {r.text[:100]}")
                return False
        except Exception as e:
            log.error(f"Telegram exception: {e}")
            return False

    return True


def send_daily_summary(config: dict, stats: dict):
    """Send a daily summary report."""
    token   = config["telegram_token"]
    chat_id = config["telegram_chat_id"]

    if not token or token == "YOUR_BOT_TOKEN":
        return

    msg = (
        f"📊 *LinkedIn Hunter — Daily Summary*\n\n"
        f"Total jobs in DB : `{stats['total_jobs']:,}`\n"
        f"Scraped today    : `{stats['last_24h']:,}`\n"
        f"Total runs       : `{stats['total_runs']:,}`\n\n"
        f"_System running fine ✅_"
    )

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
        }, timeout=10)
    except Exception as e:
        log.error(f"Daily summary error: {e}")
