"""LinkedIn job scraping adapter."""

import re
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page

from job_autofill_app.data.models import JobListing


async def extract_job_postings(page: Page, source_url: str) -> List[JobListing]:
    """Extract job postings from LinkedIn job search or job detail pages."""
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    jobs = []

    # Check if this is a search results page or a single job page
    if "/jobs/search" in source_url or "/jobs/collections" in source_url:
        jobs = _extract_from_search(soup, source_url)
    elif "/jobs/view/" in source_url or "/jobs/" in source_url:
        job = _extract_from_detail(soup, source_url)
        if job:
            jobs = [job]

    return jobs


def _extract_from_search(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract jobs from LinkedIn search results page."""
    jobs = []

    # LinkedIn uses specific selectors for job cards
    # Modern LinkedIn uses data-job-id attribute
    cards = soup.select("li[data-job-id], div[data-job-id], [data-occludable-job-id]")

    for card in cards:
        job = _parse_linkedin_card(card, source_url)
        if job:
            jobs.append(job)

    return jobs


def _parse_linkedin_card(card, source_url: str) -> JobListing:
    """Parse a LinkedIn job card."""
    # Title - usually in a h3 or a with specific class
    title = ""
    title_elem = card.select_one("h3 a, h3 span, a[data-tracking-control-name*='job'], .job-card-list__title")
    if title_elem:
        title = title_elem.get_text(strip=True)

    # Company
    company = ""
    company_elem = card.select_one("[data-tracking-control-name*='company'], .job-card-container__company-name, .job-card-list__company")
    if company_elem:
        company = company_elem.get_text(strip=True)

    # Location
    location = ""
    location_elem = card.select_one("[data-tracking-control-name*='location'], .job-card-container__metadata-item, .job-card-list__location")
    if location_elem:
        location = location_elem.get_text(strip=True)

    # Apply URL - get from the job link
    apply_url = source_url
    link = card.select_one("a[href*='/jobs/view/'], a[data-tracking-control-name*='job']")
    if link and link.get("href"):
        apply_url = link["href"]
        if not apply_url.startswith("http"):
            apply_url = "https://www.linkedin.com" + apply_url

    # Only return if we have a title
    if title and len(title) > 2:
        return JobListing(
            source_url=source_url,
            apply_url=apply_url,
            title=title,
            company=company,
            location=location,
        )

    return None


def _extract_from_detail(soup: BeautifulSoup, source_url: str) -> JobListing:
    """Extract job from LinkedIn job detail page."""
    # Title
    title = ""
    for selector in ["h1.t-24", "h1.job-title", "h1[data-test-job-title]", ".jobs-unified-top-card__job-title"]:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break

    # Company
    company = ""
    for selector in [".jobs-unified-top-card__company-name a", ".jobs-unified-top-card__company-name", "[data-test-company-name]"]:
        elem = soup.select_one(selector)
        if elem:
            company = elem.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in [".jobs-unified-top-card__bullet", "[data-test-job-location]"]:
        elem = soup.select_one(selector)
        if elem:
            location = elem.get_text(strip=True)
            break

    # Description
    description = ""
    for selector in ["#job-details", ".jobs-description__content", ".jobs-box__html-content"]:
        elem = soup.select_one(selector)
        if elem:
            description = elem.get_text(strip=True)
            break

    # Apply URL - on detail page, the apply button usually links to external site
    apply_url = source_url
    for selector in ["a[data-tracking-control-name*='apply']", ".jobs-apply-button", "button.jobs-apply-button"]:
        elem = soup.select_one(selector)
        if elem and elem.get("href"):
            apply_url = elem["href"]
            break

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