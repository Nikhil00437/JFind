"""Generic job posting adapter using JSON-LD schema.org JobPosting and heuristics."""

import json
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import Page

from job_autofill_app.data.models import JobListing


async def extract_job_postings(page: Page, source_url: str) -> List[JobListing]:
    """Extract job postings from a page using JSON-LD and heuristic fallback."""
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    jobs = []

    # Strategy 1: JSON-LD structured data (schema.org JobPosting)
    jobs = _extract_from_json_ld(soup, source_url)
    if jobs:
        return jobs

    # Strategy 2: Heuristic extraction for listing pages
    jobs = _extract_from_heuristics(soup, source_url, page)
    if jobs:
        return jobs

    # Strategy 3: Single job posting page heuristic
    job = _extract_single_job(soup, source_url)
    if job:
        return [job]

    return []


def _extract_from_json_ld(soup: BeautifulSoup, source_url: str) -> List[JobListing]:
    """Extract JobPosting objects from JSON-LD script tags."""
    jobs = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle both single object and array of objects
        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            # Check for JobPosting type (can be in @type array or string)
            types = item.get("@type", [])
            if isinstance(types, str):
                types = [types]

            if "JobPosting" not in types:
                continue

            job = _parse_job_posting_ld(item, source_url)
            if job:
                jobs.append(job)

    return jobs


def _parse_job_posting_ld(data: dict, source_url: str) -> Optional[JobListing]:
    """Parse a single JobPosting JSON-LD object into a JobListing."""
    # Required fields
    title = data.get("title", "").strip()
    if not title:
        return None

    # Optional fields with safe extraction
    company = _extract_nested_text(data, "hiringOrganization", "name") or ""
    location = _extract_location(data)
    description = _clean_html(data.get("description", ""))
    employment_type = data.get("employmentType", "") or ""
    salary = _extract_salary(data)
    apply_url = _extract_apply_url(data, source_url)

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


def _extract_nested_text(data: dict, key1: str, key2: str) -> Optional[str]:
    """Safely extract nested text from JSON-LD."""
    obj = data.get(key1)
    if isinstance(obj, dict):
        return obj.get(key2, "").strip()
    return None


def _extract_location(data: dict) -> str:
    """Extract location string from JobPosting."""
    location = data.get("jobLocation")
    if not location:
        return ""

    if isinstance(location, list):
        location = location[0] if location else {}

    if isinstance(location, dict):
        # Can be Place with address, or PostalAddress directly
        address = location.get("address", location)
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality", ""),  # city
                address.get("addressRegion", ""),    # state/province
                address.get("addressCountry", ""),   # country
            ]
            return ", ".join(filter(None, parts))
        return str(address).strip()

    return str(location).strip()


def _extract_salary(data: dict) -> str:
    """Extract salary information from JobPosting."""
    salary = data.get("baseSalary")
    if not salary:
        return ""

    if isinstance(salary, dict):
        value = salary.get("value", {})
        if isinstance(value, dict):
            # QuantitativeValue
            min_val = value.get("minValue", "")
            max_val = value.get("maxValue", "")
            unit = value.get("unitText", "")
            currency = salary.get("currency", "")
            parts = filter(None, [currency, min_val, max_val, unit])
            return " ".join(parts)
        return str(value)

    return str(salary)


def _extract_apply_url(data: dict, fallback_url: str) -> str:
    """Extract application URL from JobPosting."""
    # Try direct apply URL
    apply_url = data.get("directApply", "") or data.get("applyUrl", "") or data.get("url", "")
    if apply_url:
        return apply_url

    # Try from hiringOrganization
    org = data.get("hiringOrganization")
    if isinstance(org, dict):
        return org.get("url", "") or org.get("sameAs", "")

    return fallback_url


def _clean_html(html: str) -> str:
    """Clean HTML description to plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    # Replace common block elements with newlines
    for tag in soup.find_all(["p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.insert_after("\n")
    text = soup.get_text(separator="\n")
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_from_heuristics(soup: BeautifulSoup, source_url: str, page: Page) -> List[JobListing]:
    """Heuristic extraction for job listing/search pages."""
    jobs = []

    # Common patterns for job cards
    card_selectors = [
        "[data-job-id]",
        "[data-jobid]",
        ".job-card",
        ".job-listing",
        ".job-item",
        ".search-result",
        ".result-card",
        "article.job",
        "li.job",
        "[class*='job'][class*='card']",
        "[class*='Job'][class*='Card']",
    ]

    cards = []
    for selector in card_selectors:
        cards = soup.select(selector)
        if cards:
            break

    # If no cards found, try finding repeated anchor patterns
    if not cards:
        cards = _find_repeated_job_anchors(soup)

    for card in cards:
        job = _parse_job_card(card, source_url)
        if job:
            jobs.append(job)

    return jobs


def _find_repeated_job_anchors(soup: BeautifulSoup) -> List:
    """Find repeated anchor patterns that look like job listings."""
    # Look for links with job-related text
    anchors = soup.find_all("a", href=True)
    job_anchors = []

    for a in anchors:
        text = a.get_text(strip=True).lower()
        href = a.get("href", "")
        # Heuristics: link text looks like a job title, or href contains job/apply
        if any(kw in text for kw in ["apply", "view job", "job details", "see more"]) or \
           any(kw in href.lower() for kw in ["/job/", "/jobs/", "/careers/", "/position/"]):
            # Get the parent container that likely holds the full card
            parent = a.find_parent(["div", "li", "article", "section"])
            if parent and parent not in job_anchors:
                job_anchors.append(parent)

    return job_anchors[:50]  # Limit to reasonable number


def _parse_job_card(card, source_url: str) -> Optional[JobListing]:
    """Parse a job card element into a JobListing."""
    # Try to find title
    title_elem = card.find(["h1", "h2", "h3", "h4", "h5", "a", "span"], class_=re.compile(r"title|name|position", re.I))
    if not title_elem:
        title_elem = card.find("a")
    title = title_elem.get_text(strip=True) if title_elem else ""
    if not title or len(title) < 3:
        return None

    # Try to find company
    company_elem = card.find(class_=re.compile(r"company|employer|organization", re.I))
    company = company_elem.get_text(strip=True) if company_elem else ""

    # Try to find location
    location_elem = card.find(class_=re.compile(r"location|place|city|region", re.I))
    location = location_elem.get_text(strip=True) if location_elem else ""

    # Try to find apply/link URL
    apply_url = source_url
    link = card.find("a", href=True)
    if link:
        apply_url = link["href"]
        if not apply_url.startswith("http"):
            from urllib.parse import urljoin
            apply_url = urljoin(source_url, apply_url)

    # Try to find snippet/description
    desc_elem = card.find(class_=re.compile(r"description|snippet|summary|excerpt", re.I))
    description = desc_elem.get_text(strip=True) if desc_elem else ""

    return JobListing(
        source_url=source_url,
        apply_url=apply_url,
        title=title,
        company=company,
        location=location,
        description=description,
    )


def _extract_single_job(soup: BeautifulSoup, source_url: str) -> Optional[JobListing]:
    """Extract a single job posting from a detail page."""
    # Try to find title in common locations
    title = ""
    for selector in ["h1", "[class*='title']", "[class*='position']", "[data-test*='title']"]:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            if title and len(title) > 3:
                break

    if not title:
        return None

    # Company
    company = ""
    for selector in ["[class*='company']", "[class*='employer']", "[class*='organization']"]:
        elem = soup.select_one(selector)
        if elem:
            company = elem.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in ["[class*='location']", "[class*='place']", "[class*='city']"]:
        elem = soup.select_one(selector)
        if elem:
            location = elem.get_text(strip=True)
            break

    # Description
    description = ""
    for selector in ["[class*='description']", "[class*='details']", "[id*='description']", "main", "article"]:
        elem = soup.select_one(selector)
        if elem:
            description = _clean_html(str(elem))
            break

    # Apply URL - look for apply buttons/links
    apply_url = source_url
    for selector in ["a[href*='apply']", "button[class*='apply']", "[data-test*='apply']"]:
        elem = soup.select_one(selector)
        if elem and elem.get("href"):
            apply_url = elem["href"]
            break

    return JobListing(
        source_url=source_url,
        apply_url=apply_url,
        title=title,
        company=company,
        location=location,
        description=description,
    )