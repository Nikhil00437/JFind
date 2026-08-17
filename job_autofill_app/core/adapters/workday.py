"""Workday ATS job scraping adapter."""

import re
import json
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page
from urllib.parse import urljoin, urlparse

from job_autofill_app.data.models import JobListing


async def extract_job_postings(page: Page, source_url: str) -> List[JobListing]:
    """Extract job postings from Workday career sites."""
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    jobs = []

    # Workday sites can be job search pages or job detail pages
    # They often use AJAX/JSON APIs, so we try multiple approaches

    # Strategy 1: Look for JSON-LD (Workday sometimes includes it)
    jobs = _extract_from_json_ld(soup, source_url)
    if jobs:
        return jobs

    # Strategy 2: Look for job data in script tags (Workday often embeds data)
    jobs = _extract_from_embedded_data(soup, source_url)
    if jobs:
        return jobs

    # Strategy 3: Heuristic DOM parsing
    if "/job/" in source_url or "/careers/" in source_url:
        job = _extract_from_detail(soup, source_url)
        if job:
            return [job]

    return jobs


def _extract_from_json_ld(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract from JSON-LD structured data."""
    jobs = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            types = item.get("@type", [])
            if isinstance(types, str):
                types = [types]

            if "JobPosting" in types:
                job = _parse_job_posting_ld(item, source_url)
                if job:
                    jobs.append(job)

    return jobs


def _parse_job_posting_ld(data: dict, source_url: str) -> JobListing:
    """Parse a JobPosting JSON-LD object."""
    title = data.get("title", "").strip()
    if not title:
        return None

    company = data.get("hiringOrganization", {}).get("name", "") if isinstance(data.get("hiringOrganization"), dict) else ""
    location = _extract_location(data)
    description = data.get("description", "")
    employment_type = data.get("employmentType", "") or ""
    salary = _extract_salary(data)
    apply_url = data.get("directApply", "") or data.get("applyUrl", "") or data.get("url", "") or source_url

    return JobListing(
        source_url=source_url,
        apply_url=apply_url,
        title=title,
        company=company,
        location=location,
        description=description,
        employment_type=employment_type,
        salary=salary,
    )


def _extract_location(data: dict) -> str:
    location = data.get("jobLocation")
    if not location:
        return ""
    if isinstance(location, list):
        location = location[0] if location else {}
    if isinstance(location, dict):
        address = location.get("address", location)
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality", ""),
                address.get("addressRegion", ""),
                address.get("addressCountry", ""),
            ]
            return ", ".join(filter(None, parts))
        return str(address).strip()
    return str(location).strip()


def _extract_salary(data: dict) -> str:
    salary = data.get("baseSalary")
    if not salary:
        return ""
    if isinstance(salary, dict):
        value = salary.get("value", {})
        if isinstance(value, dict):
            min_val = value.get("minValue", "")
            max_val = value.get("maxValue", "")
            unit = value.get("unitText", "")
            currency = salary.get("currency", "")
            parts = filter(None, [currency, min_val, max_val, unit])
            return " ".join(parts)
        return str(value)
    return str(salary)


def _extract_from_embedded_data(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract job data from Workday's embedded JavaScript data."""
    jobs = []

    # Workday often embeds job data in script tags
    for script in soup.find_all("script"):
        if not script.string:
            continue

        text = script.string

        # Look for common Workday data patterns
        patterns = [
            r'jobPostings\s*[:=]\s*(\[.*?\])',
            r'jobs\s*[:=]\s*(\[.*?\])',
            r'jobData\s*[:=]\s*(\[.*?\])',
            r'searchResults\s*[:=]\s*(\[.*?\])',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    job_list = json.loads(match)
                    if isinstance(job_list, list):
                        for job_data in job_list:
                            job = _parse_workday_job_data(job_data, source_url)
                            if job:
                                jobs.append(job)
                except json.JSONDecodeError:
                    continue

    return jobs


def _parse_workday_job_data(data: dict, source_url: str) -> JobListing:
    """Parse Workday job data object."""
    # Workday job objects have various field names
    title = data.get("title") or data.get("jobTitle") or data.get("positionTitle") or ""
    if not title:
        return None

    company = data.get("company") or data.get("organization") or data.get("hiringOrganization", {}).get("name", "") or ""
    location = data.get("location") or data.get("jobLocation") or data.get("locations", [{}])[0].get("name", "") or ""
    description = data.get("description") or data.get("jobDescription") or ""
    employment_type = data.get("employmentType") or data.get("jobType") or ""
    salary = data.get("salary") or data.get("compensation") or ""

    # Apply URL - Workday often uses relative paths
    apply_url = source_url
    for key in ["applyUrl", "applyURL", "jobUrl", "url", "link", "externalUrl"]:
        if data.get(key):
            apply_url = data[key]
            break

    if not apply_url.startswith("http"):
        apply_url = urljoin(source_url, apply_url)

    return JobListing(
        source_url=source_url,
        apply_url=apply_url,
        title=title,
        company=company,
        location=location,
        description=description,
        employment_type=employment_type,
        salary=salary,
    )


def _extract_from_detail(soup: BeautifulSoup, source_url: str) -> JobListing:
    """Extract job from Workday job detail page."""
    # Title
    title = ""
    for selector in ["h1[data-automation-id='jobTitle'], .job-title, h1.css-1vg6q84, [data-qa='job-title']"]:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break

    # Company
    company = ""
    for selector in [".company-name, [data-automation-id='companyName'], .css-1n5z6z9"]:
        elem = soup.select_one(selector)
        if elem:
            company = elem.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in [".job-location, [data-automation-id='location'], .css-1v5elnn"]:
        elem = soup.select_one(selector)
        if elem:
            location = elem.get_text(strip=True)
            break

    # Description
    description = ""
    for selector in [".job-description, [data-automation-id='jobDescription'], #jobDescription"]:
        elem = soup.select_one(selector)
        if elem:
            description = elem.get_text(strip=True)
            break

    # Apply URL
    apply_url = source_url
    for selector in ["a[data-automation-id='applyButton'], .apply-button, button[data-automation-id='applyButton']"]:
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