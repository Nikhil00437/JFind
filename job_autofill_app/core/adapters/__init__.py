"""Job scraping adapters package."""

from job_autofill_app.core.adapters import generic, linkedin, indeed, glassdoor, greenhouse, lever, workday

__all__ = [
    "generic",
    "linkedin",
    "indeed",
    "glassdoor",
    "greenhouse",
    "lever",
    "workday",
]