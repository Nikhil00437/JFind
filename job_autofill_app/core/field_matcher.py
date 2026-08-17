"""Field matching logic for mapping profile data to form fields.

This module handles the intelligent matching of profile fields to form input
elements using a variety of strategies:
1. Known ATS field name mappings (Greenhouse, Lever, Workday, etc.)
2. Label/aria-label/placeholder text matching with fuzzy string matching
3. HTML attribute analysis (name, id, type, autocomplete)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
from bs4 import BeautifulSoup


@dataclass
class FormField:
    """Represents a form field element with its attributes."""
    selector: str
    tag_name: str
    input_type: str
    name: str
    id: str
    label: str
    placeholder: str
    aria_label: str
    autocomplete: str
    required: bool
    options: List[str] = None  # For select/radio/checkbox options

    def __post_init__(self):
        if self.options is None:
            self.options = []


@dataclass
class FieldMatch:
    """Represents a match between a profile field and a form field."""
    profile_field: str
    form_field: FormField
    confidence: float
    match_method: str  # "ats_map", "label_fuzzy", "attribute_fuzzy", "autocomplete"
    profile_value: str


# Known ATS field mappings
ATS_FIELD_MAPS = {
    "greenhouse": {
        "full_name": ["first_name", "last_name", "name"],
        "email": ["email"],
        "phone": ["phone"],
        "address": ["address"],
        "city": ["city"],
        "state": ["state"],
        "country": ["country"],
        "linkedin": ["linkedin", "linkedin_url"],
        "github": ["github", "github_url"],
        "portfolio": ["portfolio", "portfolio_url", "website"],
        "resume": ["resume", "resume_file"],
        "cover_letter": ["cover_letter", "cover_letter_file"],
        "education": ["education"],
        "experience": ["experience"],
        "skills": ["skills"],
    },
    "lever": {
        "full_name": ["name"],
        "email": ["email"],
        "phone": ["phone"],
        "linkedin": ["linkedin"],
        "github": ["github"],
        "portfolio": ["portfolio", "website"],
        "resume": ["resume"],
        "cover_letter": ["coverLetter", "cover_letter"],
    },
    "workday": {
        "full_name": ["firstName", "lastName", "legalFirstName", "legalLastName"],
        "email": ["emailAddress", "email"],
        "phone": ["phoneNumber", "phone"],
        "address": ["addressLine1", "addressLine2"],
        "city": ["city"],
        "state": ["state", "province"],
        "country": ["country"],
        "linkedin": ["linkedInProfile", "linkedin"],
        "resume": ["resume", "resumeFile"],
        "cover_letter": ["coverLetter", "coverLetterFile"],
    },
    "generic": {
        "full_name": ["name", "fullname", "full_name", "applicant_name", "candidate_name"],
        "email": ["email", "email_address", "mail", "e-mail"],
        "phone": ["phone", "telephone", "mobile", "cell", "phone_number"],
        "address": ["address", "street", "street_address", "address1", "address_line1"],
        "city": ["city", "town"],
        "state": ["state", "province", "region"],
        "country": ["country", "nation"],
        "linkedin": ["linkedin", "linkedin_url", "linkedin_profile"],
        "github": ["github", "github_url", "github_profile"],
        "portfolio": ["portfolio", "portfolio_url", "website", "personal_website", "url"],
        "resume": ["resume", "cv", "resume_file", "cv_file", "upload_resume"],
        "cover_letter": ["cover_letter", "coverletter", "cover_letter_file", "motivation_letter"],
    },
}


# Profile field definitions with their display labels and possible variations
PROFILE_FIELDS = {
    "full_name": {"label": "Full Name", "variations": ["full name", "name", "your name", "applicant name"]},
    "email": {"label": "Email", "variations": ["email", "email address", "e-mail", "mail"]},
    "phone": {"label": "Phone", "variations": ["phone", "telephone", "mobile", "cell phone", "phone number"]},
    "address": {"label": "Address", "variations": ["address", "street address", "street", "address line 1"]},
    "city": {"label": "City", "variations": ["city", "town"]},
    "state": {"label": "State/Province", "variations": ["state", "province", "region"]},
    "country": {"label": "Country", "variations": ["country", "nation"]},
    "linkedin": {"label": "LinkedIn", "variations": ["linkedin", "linkedin profile", "linkedin url"]},
    "github": {"label": "GitHub", "variations": ["github", "github profile", "github url"]},
    "portfolio": {"label": "Portfolio/Website", "variations": ["portfolio", "website", "personal website", "portfolio url"]},
    "resume": {"label": "Resume/CV", "variations": ["resume", "cv", "resume file", "upload resume"]},
    "cover_letter": {"label": "Cover Letter", "variations": ["cover letter", "motivation letter", "cover letter file"]},
}


def detect_ats(page_html: str, url: str) -> str:
    """Detect which ATS platform is being used based on HTML and URL."""
    url_lower = url.lower()
    html_lower = page_html.lower()

    if "greenhouse.io" in url_lower or "greenhouse" in html_lower:
        return "greenhouse"
    elif "lever.co" in url_lower or "lever" in html_lower:
        return "lever"
    elif "workday" in url_lower or "workday" in html_lower:
        return "workday"
    elif "icims" in url_lower or "icims" in html_lower:
        return "icims"
    elif "smartrecruiters" in url_lower or "smartrecruiters" in html_lower:
        return "smartrecruiters"
    elif "bamboohr" in url_lower or "bamboohr" in html_lower:
        return "bamboohr"
    elif "jobvite" in url_lower or "jobvite" in html_lower:
        return "jobvite"
    return "generic"


def extract_form_fields(page: "Page") -> List[FormField]:
    """Extract all form fields from a page using Playwright."""
    # This will be implemented with Playwright evaluation
    # For now, returning empty list - actual implementation in autofill.py
    return []


def match_fields(profile: "Profile", form_fields: List[FormField], ats_type: str = "generic") -> List[FieldMatch]:
    """Match profile fields to form fields using multiple strategies."""
    matches = []
    ats_map = ATS_FIELD_MAPS.get(ats_type, ATS_FIELD_MAPS["generic"])

    # Build profile field values
    profile_values = _build_profile_values(profile)

    for form_field in form_fields:
        best_match = _find_best_match(form_field, profile_values, ats_map)
        if best_match:
            matches.append(best_match)

    return matches


def _build_profile_values(profile: "Profile") -> Dict[str, str]:
    """Build a flat dictionary of profile field keys to their string values."""
    values = {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "country": profile.country,
        "linkedin": profile.links.get("linkedin", ""),
        "github": profile.links.get("github", ""),
        "portfolio": profile.links.get("portfolio", ""),
        "resume": profile.resume_path,
        "cover_letter": profile.cover_letter_template,
    }

    # Add education as concatenated string
    if profile.education:
        edu_parts = []
        for edu in profile.education:
            parts = [edu.get("school", ""), edu.get("degree", ""), edu.get("field", "")]
            edu_parts.append(" ".join(filter(None, parts)))
        values["education"] = "; ".join(edu_parts)

    # Add experience as concatenated string
    if profile.experience:
        exp_parts = []
        for exp in profile.experience:
            parts = [exp.get("company", ""), exp.get("title", ""), exp.get("description", "")]
            exp_parts.append(" ".join(filter(None, parts)))
        values["experience"] = "; ".join(exp_parts)

    # Add skills as comma-separated
    if profile.skills:
        values["skills"] = ", ".join(profile.skills)

    return values


def _find_best_match(form_field: FormField, profile_values: Dict[str, str], ats_map: Dict) -> Optional[FieldMatch]:
    """Find the best profile field match for a form field."""
    # Collect all text signals from the form field
    signals = [
        form_field.name,
        form_field.id,
        form_field.label,
        form_field.placeholder,
        form_field.aria_label,
        form_field.autocomplete,
    ]
    signals = [s.lower() for s in signals if s]

    if not signals:
        return None

    # Strategy 1: ATS-specific field name mapping
    for profile_key, ats_names in ats_map.items():
        for signal in signals:
            for ats_name in ats_names:
                if ats_name.lower() in signal or signal in ats_name.lower():
                    if profile_values.get(profile_key):
                        return FieldMatch(
                            profile_field=profile_key,
                            form_field=form_field,
                            confidence=0.95,
                            match_method="ats_map",
                            profile_value=profile_values[profile_key],
                        )

    # Strategy 2: Fuzzy match against profile field variations
    best_score = 0
    best_field = None
    best_method = ""

    for profile_key, field_info in PROFILE_FIELDS.items():
        if not profile_values.get(profile_key):
            continue

        for signal in signals:
            # Match against label variations
            for variation in field_info["variations"]:
                score = fuzz.partial_ratio(signal, variation.lower())
                if score > best_score and score >= 75:
                    best_score = score
                    best_field = profile_key
                    best_method = "label_fuzzy"

            # Match against profile field key itself
            score = fuzz.partial_ratio(signal, profile_key.replace("_", " "))
            if score > best_score and score >= 75:
                best_score = score
                best_field = profile_key
                best_method = "attribute_fuzzy"

    if best_field and profile_values.get(best_field):
        return FieldMatch(
            profile_field=best_field,
            form_field=form_field,
            confidence=best_score / 100.0,
            match_method=best_method,
            profile_value=profile_values[best_field],
        )

    return None


def get_unmatched_fields(form_fields: List[FormField], matches: List[FieldMatch]) -> List[FormField]:
    """Get form fields that weren't matched to any profile field."""
    matched_selectors = {m.form_field.selector for m in matches}
    return [f for f in form_fields if f.selector not in matched_selectors]