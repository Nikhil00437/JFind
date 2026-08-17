"""Main scraper orchestrator - routes URLs to appropriate adapters.

This module provides the main entry point for scraping job postings.
It detects the site/ATS from the URL and routes to the appropriate adapter.
"""

from typing import List
from urllib.parse import urlparse
from playwright.async_api import Page

from job_autofill_app.data.models import JobListing
from job_autofill_app.core.adapters import generic, linkedin, indeed, glassdoor, greenhouse, lever, workday
from job_autofill_app.core.browser_session import BrowserSession


# Adapter registry: domain patterns -> adapter module
ADAPTER_REGISTRY = {
    "linkedin.com": linkedin,
    "indeed.com": indeed,
    "indeed.ca": indeed,
    "indeed.co.uk": indeed,
    "indeed.de": indeed,
    "indeed.fr": indeed,
    "glassdoor.com": glassdoor,
    "glassdoor.ca": glassdoor,
    "greenhouse.io": greenhouse,
    "lever.co": lever,
    "workday.com": workday,
    "myworkdayjobs.com": workday,
    "workdayjobs.com": workday,
}


def get_adapter_for_url(url: str):
    """Get the appropriate adapter module for a given URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")

    # Check for exact domain matches
    for pattern, adapter in ADAPTER_REGISTRY.items():
        if pattern in domain:
            return adapter

    # Check for Workday subdomains (company.workdayjobs.com, etc.)
    if "workday" in domain or "myworkdayjobs" in domain:
        return workday

    # Check for Greenhouse subdomains (boards.greenhouse.io/...)
    if "greenhouse" in domain:
        return greenhouse

    # Check for Lever subdomains (jobs.lever.co/...)
    if "lever" in domain:
        return lever

    # Default to generic adapter
    return generic


async def scrape_url(url: str, headless: bool = True) -> List[JobListing]:
    """Main entry point: scrape a URL for job postings.

    Args:
        url: The URL to scrape (job board, search results, or single job)
        headless: Whether to run browser in headless mode

    Returns:
        List of JobListing objects found on the page
    """
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL: must start with http:// or https://")

    session = BrowserSession(headless=headless)
    context = await session.start()

    try:
        page = await context.new_page()

        # Navigate to the page
        await page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait a bit for dynamic content
        await page.wait_for_timeout(2000)

        # Get the appropriate adapter
        adapter = get_adapter_for_url(url)

        # Extract job postings
        jobs = await adapter.extract_job_postings(page, url)

        return jobs

    finally:
        await session.close()


async def scrape_multiple_urls(urls: List[str], headless: bool = True) -> List[JobListing]:
    """Scrape multiple URLs in sequence using the same browser session."""
    if not urls:
        return []

    session = BrowserSession(headless=headless)
    context = await session.start()

    all_jobs = []

    try:
        for url in urls:
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(2000)

                adapter = get_adapter_for_url(url)
                jobs = await adapter.extract_job_postings(page, url)
                all_jobs.extend(jobs)

                await page.close()
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        return all_jobs

    finally:
        await session.close()


def register_adapter(domain_pattern: str, adapter_module):
    """Register a custom adapter for a domain pattern.

    Args:
        domain_pattern: Domain pattern to match (e.g., "mycompany.com")
        adapter_module: Module with extract_job_postings(page, url) function
    """
    ADAPTER_REGISTRY[domain_pattern.lower()] = adapter_module


# Export for external use
__all__ = [
    "scrape_url",
    "scrape_multiple_urls",
    "get_adapter_for_url",
    "register_adapter",
    "ADAPTER_REGISTRY",
]