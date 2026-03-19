"""
LinkedIn Hunter - Central Configuration
Edit this file before running anything else
"""

import os


CONFIG = {
    # Neon Postgres connection string
    # Example: postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
    "neon_database_url": os.getenv("NEON_DATABASE_URL", "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"),

    # Receiver API settings (worker data lands here first)
    "receiver_host": os.getenv("RECEIVER_HOST", "0.0.0.0"),
    "receiver_port": int(os.getenv("RECEIVER_PORT", "8765")),
    "receiver_secret": os.getenv("RECEIVER_SECRET", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"),

    # Public URL for workers (used in setup docs and auto_setup secret)
    # Example: https://your-domain.com/receive or https://xyz.ngrok-free.app/receive
    "receiver_url": os.getenv("RECEIVER_URL", "https://YOUR_PUBLIC_RECEIVER_URL/receive"),

    # GitHub worker accounts with PAT scopes: repo, workflow
    "github_accounts": [
        {"username": "YOUR_GITHUB_USERNAME", "token": "ghp_YOUR_TOKEN", "repo": "lh-worker-1"},
    ],

    # ── Job Search Targets ─────────────────────────────────
    "search_jobs": [
        {"keyword": "Software Developer",        "location": "India"},
        {"keyword": "Python Developer",           "location": "India"},
        {"keyword": "React Developer",            "location": "India"},
        {"keyword": "Full Stack Developer",       "location": "India"},
        {"keyword": "Backend Developer",          "location": "India"},
        {"keyword": "Frontend Developer",         "location": "India"},
        {"keyword": "Java Developer",             "location": "India"},
        {"keyword": "Node.js Developer",          "location": "India"},
        {"keyword": "Data Engineer",              "location": "India"},
        {"keyword": "DevOps Engineer",            "location": "India"},
        {"keyword": "Software Engineer",          "location": "Bangalore"},
        {"keyword": "Software Engineer",          "location": "Hyderabad"},
        {"keyword": "Software Engineer",          "location": "Chennai"},
        {"keyword": "Software Engineer",          "location": "Mumbai"},
        {"keyword": "Software Engineer",          "location": "Pune"},
    ],

    # ── Your Skills Filter (jobs matching these get alerted) ─
    "alert_keywords": [
        "python", "react", "javascript", "node", "django",
        "fastapi", "flask", "typescript", "aws", "docker"
        # ADD YOUR OWN SKILLS HERE
    ],

    # ── Telegram Alerts (optional) ─────────────────────────
    "telegram_token": os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN"),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID"),

    # ── Scheduling ─────────────────────────────────────────
    # How often to trigger a new batch (minutes)
    "trigger_interval_minutes": 10,

    # Jobs per GitHub Actions run (15-25 recommended)
    "jobs_per_run": 20,

    # Date filter: r3600=1hr, r86400=24hr, r604800=1week
    "linkedin_date_filter": "r86400",
}
