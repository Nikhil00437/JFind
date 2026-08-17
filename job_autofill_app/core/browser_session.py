"""Shared Playwright persistent browser context for scraping and auto-fill.

This module provides a single persistent browser context that maintains
cookies, localStorage, and session state across both scraping and auto-fill
operations. This allows login sessions to persist between scraping a job
board and auto-filling an application on the same domain.
"""

from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright


class BrowserSession:
    """Manages a persistent Playwright browser context shared across the app."""

    _instance: Optional["BrowserSession"] = None
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, headless: bool = True, user_data_dir: Optional[str] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.headless = headless
        self.user_data_dir = user_data_dir or str(Path.home() / ".job_autofill_app" / "browser_profile")
        self._initialized = True

    async def start(self) -> BrowserContext:
        """Start the browser and return the persistent context."""
        if self._context is not None:
            return self._context

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            permissions=["clipboard-read", "clipboard-write"],
        )
        self._context = self._browser
        return self._context

    async def get_context(self) -> BrowserContext:
        """Get the browser context, starting it if necessary."""
        if self._context is None:
            await self.start()
        return self._context

    async def new_page(self) -> Page:
        """Create a new page in the persistent context."""
        context = await self.get_context()
        return await context.new_page()

    async def close(self):
        """Close the browser and cleanup."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def set_headless(self, headless: bool):
        """Set headless mode (requires restart to take effect)."""
        self.headless = headless

    async def __aenter__(self) -> BrowserContext:
        return await self.get_context()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience function for quick access
async def get_browser_session(headless: bool = True) -> BrowserSession:
    """Get the singleton browser session instance."""
    session = BrowserSession(headless=headless)
    await session.start()
    return session