"""Indeed job scraping adapter."""

import re
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page
from urllib.parse import urljoin

from job_autofill_app.data.models import JobListing


async def extract_job_postings(page: Page, source_url: str) -> List[JobListing]:
    """Extract job postings from Indeed search results or job detail pages."""
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    jobs = []

    # Check if this is a search results page or a single job page
    if "/jobs?q=" in source_url or "/jobs?" in source_url or "/jobsearch" in source_url:
        jobs = _extract_from_search(soup, source_url)
    elif "/viewjob" in source_url or "/job/" in source_url:
        job = _extract_from_detail(soup, source_url)
        if job:
            jobs = [job]

    return jobs


def _extract_from_search(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract jobs from Indeed search results page."""
    jobs = []

    # Indeed uses various card selectors
    cards = soup.select(
        "[data-jk], "
        ".job_seen_beacon, "
        ".resultContent, "
        ".tapItem, "
        "[data-testid='job-card']"
    )

    for card in cards:
        job = _parse_indeed_card(card, source_url)
        if job:
            jobs.append(job)

    return jobs


def _parse_indeed_card(card, source_url: str) -> JobListing:
    """Parse an Indeed job card."""
    # Title
    title = ""
    title_elem = card.select_one("h2 a, h2 span, [data-testid='job-title'], .jobTitle a")
    if title_elem:
        title = title_elem.get_text(strip=True)

    # Company
    company = ""
    company_elem = card.select_one("[data-testid='company-name'], .companyName, .company_location")
    if company_elem:
        company = company_elem.get_text(strip=True)

    # Location
    location = ""
    location_elem = card.select_one("[data-testid='job-location'], .companyLocation, .location")
    if location_elem:
        location = location_elem.get_text(strip=True)

    # Apply URL
    apply_url = source_url
    link = card.select_one("h2 a, [data-testid='job-title'] a, a.jcs-JobTitle")
    if link and link.get("href"):
        href = link["href"]
        if not href.startswith("http"):
            apply_url = urljoin("https://www.indeed.com", href)
        else:
            apply_url = href

    # Salary
    salary = ""
    salary_elem = card.select_one("[data-testid='salary'], .salary-snippet, .estimated-salary")
    if salary_elem:
        salary = salary_elem.get_text(strip=True)

    if title and len(title) > 2:
        return JobListing(
            source_url=source_url,
            apply_url=apply_url,
            title=title,
            company=company,
            location=location,
            salary=salary,
        )

    return None


def _extract_from_detail(soup: BeautifulSoup, source_url: str) -> JobListing:
    """Extract job from Indeed job detail page."""
    # Title
    title = ""
    for selector in ["h1.jobsearch-JobInfoHeader-title", "h1[data-testid='jobsearch-JobInfoHeader-title']", ".jobsearch-JobInfoHeader-title"]:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break

    # Company
    company = ""
    for selector in [".jobsearch-CompanyInfoContainer a", "[data-testid='company-name']", ".jobsearch-InlineCompanyRating"]:
        elem = soup.select_one(selector)
        if elem:
            company = elem.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in [".jobsearch-JobInfoHeader-location", "[data-testid='job-location']", ".jobsearch-CompanyInfoContainer div"]:
        elem = soup.select_one(selector)
        if elem:
            location = elem.get_text(strip=True)
            break

    # Description
    description = ""
    for selector in ["#jobDescriptionText", "[data-testid='job-description']", ".jobsearch-jobDescriptionText"]:
        elem = soup.select_one(selector)
        if elem:
            description = elem.get_text(strip=True)
            break

    # Salary
    salary = ""
    for selector in [".jobsearch-SalaryAttribute", "[data-testid='salary']", ".salaryInfo"]:
        elem = soup.select_one(selector)
        if elem:
            salary = elem.get_text(strip=True)
            break

    # Apply URL - on Indeed detail page, apply button often goes to external site
    apply_url = source_url
    for selector in ["#applyButtonLinkContainer a", "[data-testid='apply-button']", "a[href*='apply']"]:
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
            salary=salary,
        )

    return None