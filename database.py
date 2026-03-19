"""
database.py — Neon Postgres storage layer
Stores every field extracted by the scraper.
"""

import logging
from datetime import datetime

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

log = logging.getLogger(__name__)

ALL_JOB_FIELDS = [
    "id", "scraped_at", "source",
    "job_title", "job_url", "job_description",
    "job_type", "seniority_level", "work_mode",
    "posted_date", "posted_time", "posted_datetime_raw",
    "applicant_count", "salary_min", "salary_max",
    "salary_currency", "salary_period",
    "required_skills", "industries", "job_functions",
    "company_name", "company_linkedin_url", "company_website",
    "company_size", "company_size_min", "company_size_max",
    "company_founded", "company_hq", "company_type",
    "company_industry", "company_description", "company_specialities",
    "poster_name", "poster_title", "poster_linkedin_url", "poster_image_url",
    "alerted", "keyword",
]


def get_conn(database_url: str):
    return psycopg.connect(database_url, row_factory=dict_row)


def init_db(database_url: str):
    with get_conn(database_url) as conn:
        with conn.cursor() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id                    TEXT PRIMARY KEY,
                    scraped_at            TIMESTAMPTZ,
                    source                TEXT,

                    job_title             TEXT,
                    job_url               TEXT,
                    job_description       TEXT,
                    job_type              TEXT,
                    seniority_level       TEXT,
                    work_mode             TEXT,
                    posted_date           TEXT,
                    posted_time           TEXT,
                    posted_datetime_raw   TEXT,
                    applicant_count       TEXT,
                    salary_min            INTEGER,
                    salary_max            INTEGER,
                    salary_currency       TEXT,
                    salary_period         TEXT,
                    required_skills       TEXT,
                    industries            TEXT,
                    job_functions         TEXT,

                    company_name          TEXT,
                    company_linkedin_url  TEXT,
                    company_website       TEXT,
                    company_size          TEXT,
                    company_size_min      INTEGER,
                    company_size_max      INTEGER,
                    company_founded       TEXT,
                    company_hq            TEXT,
                    company_type          TEXT,
                    company_industry      TEXT,
                    company_description   TEXT,
                    company_specialities  TEXT,

                    poster_name           TEXT,
                    poster_title          TEXT,
                    poster_linkedin_url   TEXT,
                    poster_image_url      TEXT,

                    alerted               INTEGER DEFAULT 0,
                    keyword               TEXT
                )
                """
            )

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    github_user TEXT,
                    keyword     TEXT,
                    jobs_found  INTEGER,
                    jobs_new    INTEGER,
                    run_at      TIMESTAMPTZ
                )
                """
            )

            c.execute("CREATE INDEX IF NOT EXISTS idx_alerted ON jobs(alerted)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_posted_date ON jobs(posted_date)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_company ON jobs(company_name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_title ON jobs(job_title)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_work_mode ON jobs(work_mode)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_seniority ON jobs(seniority_level)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_company_size ON jobs(company_size_min)")

        conn.commit()
    log.info("Database initialized on Neon.")


def bulk_insert_jobs(database_url: str, jobs, keyword, github_user):
    new = 0
    dupe = 0
    now = datetime.utcnow().isoformat()

    with get_conn(database_url) as conn:
        with conn.cursor() as c:
            for job in jobs:
                job["keyword"] = keyword
                job["scraped_at"] = job.get("scraped_at") or now
                job["alerted"] = 0

                fields = [f for f in ALL_JOB_FIELDS if f in job]
                if not fields:
                    continue

                query = sql.SQL("INSERT INTO jobs ({fields}) VALUES ({values}) ON CONFLICT (id) DO NOTHING").format(
                    fields=sql.SQL(", ").join(sql.Identifier(f) for f in fields),
                    values=sql.SQL(", ").join(sql.Placeholder() for _ in fields),
                )
                c.execute(query, [job.get(f) for f in fields])
                if c.rowcount == 1:
                    new += 1
                else:
                    dupe += 1

            c.execute(
                "INSERT INTO scrape_runs (github_user, keyword, jobs_found, jobs_new, run_at) VALUES (%s,%s,%s,%s,NOW())",
                (github_user, keyword, len(jobs), new),
            )

        conn.commit()

    log.info("[%s] %s new, %s dupes", github_user, new, dupe)
    return {"new": new, "dupes": dupe, "total": len(jobs)}


def get_unalerted_jobs(database_url: str):
    with get_conn(database_url) as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM jobs WHERE alerted = 0 ORDER BY scraped_at DESC")
            return c.fetchall()


def mark_alerted(database_url: str, job_ids):
    if not job_ids:
        return
    with get_conn(database_url) as conn:
        with conn.cursor() as c:
            c.execute("UPDATE jobs SET alerted = 1 WHERE id = ANY(%s)", (job_ids,))
        conn.commit()


def get_stats(database_url: str):
    stats = {}
    with get_conn(database_url) as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) AS v FROM jobs")
            stats["total_jobs"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE alerted = 0")
            stats["unalerted"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE scraped_at >= NOW() - INTERVAL '1 day'")
            stats["last_24h"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE posted_date = TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD')")
            stats["posted_today"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE work_mode = 'Remote'")
            stats["remote_jobs"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE salary_min IS NOT NULL")
            stats["with_salary"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE poster_name IS NOT NULL")
            stats["with_poster"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM jobs WHERE company_founded IS NOT NULL")
            stats["with_company_details"] = c.fetchone()["v"]

            c.execute("SELECT COUNT(*) AS v FROM scrape_runs")
            stats["total_runs"] = c.fetchone()["v"]

    return stats


def search_jobs(database_url: str, query, filters=None, limit=50):
    q = f"%{query.lower()}%"
    where = ["(LOWER(job_title) LIKE %s OR LOWER(company_name) LIKE %s OR LOWER(job_description) LIKE %s)"]
    params = [q, q, q]

    if filters:
        if filters.get("work_mode"):
            where.append("work_mode = %s")
            params.append(filters["work_mode"])
        if filters.get("seniority_level"):
            where.append("seniority_level = %s")
            params.append(filters["seniority_level"])
        if filters.get("company_size_max"):
            where.append("company_size_min <= %s")
            params.append(filters["company_size_max"])
        if filters.get("company_size_min"):
            where.append("company_size_max >= %s")
            params.append(filters["company_size_min"])

    sql_query = f"SELECT * FROM jobs WHERE {' AND '.join(where)} ORDER BY posted_date DESC, scraped_at DESC LIMIT %s"
    params.append(limit)

    with get_conn(database_url) as conn:
        with conn.cursor() as c:
            c.execute(sql_query, params)
            return c.fetchall()
