"""Greenhouse ATS job scraping adapter."""

import re
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page
from urllib.parse import urljoin

from job_autofill_app.data.models import JobListing


async def extract_job_postings(page: Page, source_url: str) -> List[JobListing]:
    """Extract job postings from Greenhouse job board or job detail pages."""
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    jobs = []

    # Check if this is a job board page or a single job page
    if "/jobs/" in source_url and not re.search(r"/jobs/\d+", source_url):
        jobs = _extract_from_board(soup, source_url)
    else:
        job = _extract_from_detail(soup, source_url)
        if job:
            jobs = [job]

    return jobs


def _extract_from_board(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract jobs from Greenhouse job board page."""
    jobs = []

    # Greenhouse job board uses specific structure
    cards = soup.select(
        ".opening, "
        "[data-mapped='true'], "
        ".job-post, "
        "section.opening"
    )

    for card in cards:
        job = _parse_greenhouse_card(card, source_url)
        if job:
            jobs.append(job)

    return jobs


def _parse_greenhouse_card(card, source_url: str) -> JobListing:
    """Parse a Greenhouse job board card."""
    # Title
    title = ""
    title_elem = card.select_one("h2 a, .opening-title a, .job-title a")
    if title_elem:
        title = title_elem.get_text(strip=True)

    # Location
    location = ""
    location_elem = card.select_one(".location, .job-location, [data-location]")
    if location_elem:
        location = location_elem.get_text(strip=True)

    # Apply URL
    apply_url = source_url
    link = card.select_one("h2 a, .opening-title a, a[href*='/jobs/']")
    if link and link.get("href"):
        href = link["href"]
        if not href.startswith("http"):
            apply_url = urljoin(source_url, href)
        else:
            apply_url = href

    if title and len(title) > 2:
        return JobListing(
            source_url=source_url,
            apply_url=apply_url,
            title=title,
            location=location,
        )

    return None


def _extract_from_detail(soup: BeautifulSoup, source_url: str) -> JobListing:
    """Extract job from Greenhouse job detail page."""
    # Title
    title = ""
    for selector in ["h1.app-title, .job-title, h1#job-title"]:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break

    # Company - usually in the header or meta
    company = ""
    for selector in [".company-name, .board-name, [data-company]"]:
        elem = soup.select_one(selector)
        if elem:
            company = elem.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in [".location, .job-location, [data-location]"]:
        elem = soup.select_one(selector)
        if elem:
            location = elem.get_text(strip=True)
            break

    # Description
    description = ""
    for selector in [".content, .job-description, #content, .section-wrapper"]:
        elem = soup.select_one(selector)
        if elem:
            description = elem.get_text(strip=True)
            break

    # Apply URL - Greenhouse usually has an apply button
    apply_url = source_url
    for selector in ["a[href*='apply'], .apply-button, button.apply, #apply-button"]:
        elem = soup.select_one(selector)
        if elem and elem.get("href"):
            apply_url = elem["href"]
            break

    # Also check for the Greenhouse apply iframe URL pattern
    if apply_url == source_url:
        # Greenhouse apply URLs often follow pattern: /jobs/<id>/apply
        match = re.search(r"/jobs/(\d+)", source_url)
        if match:
            apply_url = f"{source_url.rstrip('/')}/apply"

    if title:
        return JobListing(
            source_url=source_url,
            apply_url=apply_url,
            title=title,
            company=company,
            location=location,
            description=description,
        )

    return None