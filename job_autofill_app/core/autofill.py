"""Auto-fill engine - Playwright-driven form filler with field mapping.

IMPORTANT SAFETY BOUNDARY: This module NEVER auto-submits forms.
It fills fields and stops before the final submit action, leaving
the browser open for the user to review and submit manually.
"""

import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from playwright.async_api import Page, ElementHandle, BrowserContext
from rapidfuzz import fuzz

from job_autofill_app.data.models import Profile
from job_autofill_app.core.field_matcher import (
    FormField, FieldMatch, extract_form_fields, match_fields, 
    detect_ats, get_unmatched_fields, ATS_FIELD_MAPS
)
from job_autofill_app.core.browser_session import BrowserSession


@dataclass
class FillResult:
    """Result of an auto-fill operation."""
    filled_fields: List[FieldMatch]
    skipped_fields: List[FormField]
    errors: List[str]
    apply_url: str


class AutoFillEngine:
    """Main auto-fill engine that drives form filling in a visible browser."""

    def __init__(self, headless: bool = False):
        # Always run headed for auto-fill so user can review
        self.headless = False
        self.session = BrowserSession(headless=False)
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Start the browser session."""
        self.context = await self.session.start()
        return self.context

    async def close(self):
        """Close the browser session."""
        await self.session.close()

    async def auto_fill(self, apply_url: str, profile: Profile) -> FillResult:
        """Main entry point: navigate to apply URL and fill form.

        Args:
            apply_url: The job application URL
            profile: User profile with data to fill

        Returns:
            FillResult with filled/skipped fields and any errors
        """
        if not self.context:
            await self.start()

        self.page = await self.context.new_page()

        try:
            # Navigate to the application page
            await self.page.goto(apply_url, wait_until="networkidle", timeout=60000)
            await self.page.wait_for_timeout(2000)

            # Detect ATS type
            html = await self.page.content()
            ats_type = detect_ats(html, apply_url)

            # Extract form fields
            form_fields = await self._extract_form_fields()

            # Match profile fields to form fields
            matches = match_fields(profile, form_fields, ats_type)

            # Fill matched fields
            filled = []
            errors = []

            for match in matches:
                try:
                    await self._fill_field(match)
                    filled.append(match)
                except Exception as e:
                    errors.append(f"Failed to fill {match.profile_field}: {str(e)}")

            # Get unmatched fields
            skipped = get_unmatched_fields(form_fields, matches)

            return FillResult(
                filled_fields=filled,
                skipped_fields=skipped,
                errors=errors,
                apply_url=apply_url,
            )

        except Exception as e:
            return FillResult(
                filled_fields=[],
                skipped_fields=[],
                errors=[f"Auto-fill failed: {str(e)}"],
                apply_url=apply_url,
            )

    async def _extract_form_fields(self) -> List[FormField]:
        """Extract all fillable form fields from the current page."""
        fields = []

        # Use Playwright to evaluate and get all form elements
        elements = await self.page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset']), "
            "textarea, select, [role='textbox'], [contenteditable='true']"
        )

        for idx, element in enumerate(elements):
            try:
                field = await self._create_form_field(element, idx)
                if field:
                    fields.append(field)
            except Exception:
                continue

        return fields

    async def _create_form_field(self, element: ElementHandle, idx: int) -> Optional[FormField]:
        """Create a FormField from a Playwright element handle."""
        # Get all attributes
        attrs = await element.evaluate("""el => {
            const attrs = {};
            for (const attr of el.attributes) {
                attrs[attr.name] = attr.value;
            }
            return attrs;
        }""")

        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        input_type = attrs.get("type", "text")

        # Skip non-fillable types
        if input_type in ["hidden", "submit", "button", "reset", "image", "file"]:
            # Still include file inputs for resume upload
            pass

        # Get label text
        label = await self._get_label_text(element, attrs)

        # Get options for select elements
        options = []
        if tag_name == "select":
            options = await element.evaluate("""el => {
                return Array.from(el.options).map(o => o.textContent.trim());
            }""")

        # Build selector
        selector = await self._build_selector(element, attrs, idx)

        return FormField(
            selector=selector,
            tag_name=tag_name,
            input_type=input_type,
            name=attrs.get("name", ""),
            id=attrs.get("id", ""),
            label=label,
            placeholder=attrs.get("placeholder", ""),
            aria_label=attrs.get("aria-label", ""),
            autocomplete=attrs.get("autocomplete", ""),
            required=attrs.get("required") is not None,
            options=options,
        )

    async def _get_label_text(self, element: ElementHandle, attrs: dict) -> str:
        """Get the label text for an element."""
        # Try aria-label first
        if attrs.get("aria-label"):
            return attrs["aria-label"]

        # Try aria-labelledby
        if attrs.get("aria-labelledby"):
            label_id = attrs["aria-labelledby"]
            label_el = await self.page.query_selector(f"#{label_id}")
            if label_el:
                return await label_el.text_content()

        # Try explicit label with for=id
        if attrs.get("id"):
            label_el = await self.page.query_selector(f"label[for='{attrs['id']}']")
            if label_el:
                return await label_el.text_content()

        # Try parent label
        label_el = await element.evaluate_handle("el => el.closest('label')")
        if label_el:
            text = await label_el.text_content()
            if text:
                return text.strip()

        # Try nearby text (previous sibling, parent text)
        nearby = await element.evaluate("""el => {
            // Get previous sibling text
            let prev = el.previousElementSibling;
            if (prev) return prev.textContent.trim();
            // Get parent text (first 200 chars)
            if (el.parentElement) return el.parentElement.textContent.trim().substring(0, 200);
            return '';
        }""")
        if nearby:
            return nearby.strip()

        return ""

    async def _build_selector(self, element: ElementHandle, attrs: dict, idx: int) -> str:
        """Build a reliable selector for the element."""
        # Prefer ID
        if attrs.get("id"):
            return f"#{attrs['id']}"

        # Prefer name
        if attrs.get("name"):
            tag = attrs.get("tagName", "").lower()
            return f"{tag}[name='{attrs['name']}']"

        # Use data attributes
        for key in ["data-testid", "data-qa", "data-cy", "data-automation-id"]:
            if attrs.get(key):
                return f"[{key}='{attrs[key]}']"

        # Fallback: nth-of-type
        return await element.evaluate("""(el, idx) => {
            const tag = el.tagName.toLowerCase();
            const parent = el.parentElement;
            if (!parent) return `${tag}:nth-of-type(${idx + 1})`;
            const siblings = Array.from(parent.children).filter(c => c.tagName === tag.toUpperCase());
            const index = siblings.indexOf(el);
            return `${tag}:nth-of-type(${index + 1})`;
        }""", idx)

    async def _fill_field(self, match: FieldMatch):
        """Fill a single form field based on the match."""
        field = match.form_field
        value = match.profile_value

        if not value:
            return

        element = await self.page.query_selector(field.selector)
        if not element:
            raise Exception(f"Element not found: {field.selector}")

        # Handle different input types
        if field.tag_name == "select":
            await self._fill_select(element, field, value)
        elif field.input_type in ["radio", "checkbox"]:
            await self._fill_radio_checkbox(element, field, value)
        elif field.input_type == "file":
            await self._fill_file(element, value)
        elif field.tag_name == "textarea" or field.input_type in ["text", "email", "tel", "url", "number"]:
            await self._fill_text(element, value)
        else:
            # Try generic fill
            await self._fill_text(element, value)

    async def _fill_text(self, element: ElementHandle, value: str):
        """Fill a text input or textarea."""
        # Clear existing value
        await element.click()
        await element.fill("")
        await element.type(value, delay=50)  # Type with delay for realism

    async def _fill_select(self, element: ElementHandle, field: FormField, value: str):
        """Fill a select dropdown."""
        # Try to match by exact text first
        for option in field.options:
            if option.lower() == value.lower():
                await element.select_option(label=option)
                return

        # Try fuzzy match
        best_match = None
        best_score = 0
        for option in field.options:
            score = fuzz.partial_ratio(option.lower(), value.lower())
            if score > best_score and score >= 70:
                best_score = score
                best_match = option

        if best_match:
            await element.select_option(label=best_match)
        else:
            # Try by value attribute
            await element.select_option(value=value)

    async def _fill_radio_checkbox(self, element: ElementHandle, field: FormField, value: str):
        """Fill radio button or checkbox."""
        # For radio/checkbox, value is typically "yes", "true", "on", etc.
        # Check if the value suggests checking
        should_check = value.lower() in ["yes", "true", "on", "1", "y", "checked"]
        
        is_checked = await element.is_checked()
        if should_check and not is_checked:
            await element.click()
        elif not should_check and is_checked:
            await element.click()

    async def _fill_file(self, element: ElementHandle, value: str):
        """Fill a file upload (resume)."""
        import os
        if os.path.exists(value):
            await element.set_input_files(value)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience function
async def run_auto_fill(apply_url: str, profile: Profile, headless: bool = False) -> FillResult:
    """Run auto-fill on a URL with a profile."""
    async with AutoFillEngine(headless=headless) as engine:
        return await engine.auto_fill(apply_url, profile)


# SAFETY NOTICE - This is a hard boundary
"""
================================================================================
AUTO-FILL SAFETY BOUNDARY - DO NOT CROSS
================================================================================

This auto-fill engine is designed to ASSIST the user, not replace them.
The following actions are EXPLICITLY FORBIDDEN in this codebase:

1. NO AUTO-SUBMIT - Never click submit, send, or apply buttons
2. NO FORM SUBMISSION - Never call form.submit() or equivalent
3. NO ENTER KEY ON SUBMIT - Never press Enter on a submit button
4. NO CONFIRMATION DIALOG AUTO-ACCEPT - Never auto-confirm modals

The engine stops after filling all matched fields and leaves the
browser open for the user to:
- Review all filled data
- Fill any skipped fields manually
- Click submit themselves

This is a deliberate design choice for:
- Legal compliance (many sites' ToS prohibit automated submission)
- User control (applications are important, user should verify)
- Account safety (auto-submit can trigger fraud detection)

If you need to add submit functionality, you must:
1. Create a separate, clearly named module
2. Add explicit user consent flow
3. Document the risks prominently
4. Never enable by default

================================================================================
"""