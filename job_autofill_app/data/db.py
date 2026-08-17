"""SQLite database layer for profile and job listing persistence."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from job_autofill_app.data.models import Profile, JobListing


DB_PATH = Path.home() / ".job_autofill_app" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    full_name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    city TEXT DEFAULT '',
    state TEXT DEFAULT '',
    country TEXT DEFAULT '',
    links TEXT DEFAULT '{}',
    education TEXT DEFAULT '[]',
    experience TEXT DEFAULT '[]',
    skills TEXT DEFAULT '[]',
    resume_path TEXT DEFAULT '',
    cover_letter_template TEXT DEFAULT '',
    qa_bank TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS job_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL,
    apply_url TEXT DEFAULT '',
    title TEXT NOT NULL,
    company TEXT DEFAULT '',
    location TEXT DEFAULT '',
    description TEXT DEFAULT '',
    employment_type TEXT DEFAULT '',
    salary TEXT DEFAULT '',
    date_scraped TEXT NOT NULL,
    status TEXT DEFAULT 'New'
);

CREATE INDEX IF NOT EXISTS idx_job_listings_status ON job_listings(status);
CREATE INDEX IF NOT EXISTS idx_job_listings_company ON job_listings(company);
CREATE INDEX IF NOT EXISTS idx_job_listings_date_scraped ON job_listings(date_scraped);
"""


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


# Profile CRUD operations

def save_profile(profile: Profile) -> Profile:
    """Save or update the user profile (singleton, id=1)."""
    with get_connection() as conn:
        data = profile.to_dict()
        # Remove id from data since we always use id=1
        data.pop("id", None)
        
        # Define column order explicitly to match schema
        columns_order = [
            "full_name", "email", "phone", "address", "city", "state", "country",
            "links", "education", "experience", "skills", "resume_path",
            "cover_letter_template", "qa_bank"
        ]
        
        # Convert dict/list fields to JSON
        json_fields = {"links", "education", "experience", "skills", "qa_bank"}
        values = []
        for col in columns_order:
            val = data.get(col, "")
            if col in json_fields:
                val = json.dumps(val)
            values.append(val)
        
        columns = ", ".join(columns_order)
        placeholders = ", ".join(["?" for _ in columns_order])
        set_clause = ", ".join([f"{col}=?" for col in columns_order])
        
        # 15 values for INSERT (id + 14 columns) + 14 values for UPDATE = 29 total
        # Note: the '1' in VALUES is a literal, not a placeholder
        # So we have 14 placeholders in VALUES + 14 in UPDATE = 28 total
        params = values + values
        
        conn.execute(f"""
            INSERT INTO profile (id, {columns}) VALUES (1, {placeholders})
            ON CONFLICT(id) DO UPDATE SET {set_clause}
        """, params)
        conn.commit()
    return get_profile()


def get_profile() -> Profile:
    """Retrieve the user profile (singleton, id=1)."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        if row:
            data = dict(row)
            # Parse JSON fields
            json_fields = {"links", "education", "experience", "skills", "qa_bank"}
            for field in json_fields:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        data[field] = {} if field in {"links", "qa_bank"} else []
            return Profile.from_dict(data)
        # Return empty profile if none exists
        return Profile(id=1)


# Job Listing CRUD operations

def save_job_listing(job: JobListing) -> JobListing:
    """Save a job listing, return the saved job with assigned ID."""
    with get_connection() as conn:
        data = job.to_dict()
        job_id = data.pop("id")
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = list(data.values())

        if job_id == 0:
            # Insert new
            cursor = conn.execute(f"INSERT INTO job_listings ({columns}) VALUES ({placeholders})", values)
            job.id = cursor.lastrowid
        else:
            # Update existing
            conn.execute(f"UPDATE job_listings SET {', '.join(f'{k}=?' for k in data.keys())} WHERE id = ?", values + [job_id])
        conn.commit()
    return job


def get_job_listing(job_id: int) -> Optional[JobListing]:
    """Retrieve a single job listing by ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM job_listings WHERE id = ?", (job_id,)).fetchone()
        if row:
            return JobListing.from_dict(dict(row))
    return None


def get_all_job_listings(status_filter: Optional[str] = None, search_query: str = "") -> List[JobListing]:
    """Retrieve all job listings, optionally filtered by status and search query."""
    with get_connection() as conn:
        query = "SELECT * FROM job_listings WHERE 1=1"
        params = []

        if status_filter and status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)

        if search_query:
            query += " AND (title LIKE ? OR company LIKE ? OR location LIKE ?)"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])

        query += " ORDER BY date_scraped DESC"

        rows = conn.execute(query, params).fetchall()
        return [JobListing.from_dict(dict(row)) for row in rows]


def update_job_status(job_id: int, status: str) -> bool:
    """Update the status of a job listing."""
    with get_connection() as conn:
        cursor = conn.execute("UPDATE job_listings SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_job_listing(job_id: int) -> bool:
    """Delete a job listing."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM job_listings WHERE id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0