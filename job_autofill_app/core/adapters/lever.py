"""Lever ATS job scraping adapter."""

import re
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page
from urllib.parse import urljoin

from job_autofill_app.data.models import JobListing


async def extract_job_postings(page: Page, source_url: str) -> List[JobListing]:
    """Extract job postings from Lever job board or job detail pages."""
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    jobs = []

    # Check if this is a job board page or a single job page
    if "/careers" in source_url or "/jobs" in source_url:
        if re.search(r"/jobs/[a-f0-9-]{36}", source_url) or re.search(r"/[a-f0-9-]{36}$", source_url):
            # Single job page (UUID in URL)
            job = _extract_from_detail(soup, source_url)
            if job:
                jobs = [job]
        else:
            # Job board page
            jobs = _extract_from_board(soup, source_url)

    return jobs


def _extract_from_board(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract jobs from Lever job board page."""
    jobs = []

    # Lever job board cards
    cards = soup.select(
        ".posting, "
        ".postings-group .posting, "
        "[data-qa='posting'], "
        ".posting-title"
    )

    for card in cards:
        job = _parse_lever_card(card, source_url)
        if job:
            jobs.append(job)

    return jobs


def _parse_lever_card(card, source_url: str) -> JobListing:
    """Parse a Lever job board card."""
    # Title
    title = ""
    title_elem = card.select_one("h5 a, .posting-title a, .posting-name a")
    if title_elem:
        title = title_elem.get_text(strip=True)

    # Location
    location = ""
    location_elem = card.select_one(".posting-categories .location, .sort-by-location, [data-qa='posting-location']")
    if location_elem:
        location = location_elem.get_text(strip=True)

    # Team/Department (often used as category)
    team = ""
    team_elem = card.select_one(".posting-categories .team, .sort-by-team, [data-qa='posting-team']")
    if team_elem:
        team = team_elem.get_text(strip=True)

    # Apply URL
    apply_url = source_url
    link = card.select_one("h5 a, .posting-title a, a[href*='/jobs/'], a[href*='/careers/']")
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
            description=team,  # Store team in description for now
        )

    return None


def _extract_from_detail(soup: BeautifulSoup, source_url: str) -> JobListing:
    """Extract job from Lever job detail page."""
    # Title
    title = ""
    for selector in ["h2.posting-title, h2.posting-name, h1.posting-headline"]:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break

    # Company - Lever doesn't always show company on detail page
    company = ""
    for selector in [".posting-company, .company-name, [data-qa='posting-company']"]:
        elem = soup.select_one(selector)
        if elem:
            company = elem.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in [".posting-categories .location, .sort-by-location, [data-qa='posting-location']"]:
        elem = soup.select_one(selector)
        if elem:
            location = elem.get_text(strip=True)
            break

    # Team/Department
    team = ""
    for selector in [".posting-categories .team, .sort-by-team, [data-qa='posting-team']"]:
        elem = soup.select_one(selector)
        if elem:
            team = elem.get_text(strip=True)
            break

    # Description
    description = ""
    for selector in [".posting-description, .description, [data-qa='posting-description'], .content"]:
        elem = soup.select_one(selector)
        if elem:
            description = elem.get_text(strip=True)
            break

    # Apply URL - Lever usually has an apply button at bottom
    apply_url = source_url
    for selector in ["a[href*='apply'], .apply-button, button.apply, [data-qa='apply-button']"]:
        elem = soup.select_one(selector)
        if elem and elem.get("href"):
            apply_url = elem["href"]
            break

    # Lever apply URLs often follow pattern: /jobs/<uuid>/apply
    if apply_url == source_url:
        match = re.search(r"/([a-f0-9-]{36})", source_url)
        if match:
            apply_url = f"{source_url.rstrip('/')}/apply"

    if title:
        return JobListing(
            source_url=source_url,
            apply_url=apply_url,
            title=title,
            company=company,
            location=location,
            description=f"{team}\n\n{description}".strip(),
        )

    return None