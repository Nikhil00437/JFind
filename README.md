# JFind — Job Scraper & Auto-Fill Desktop App

A dark-themed desktop application for scraping job listings and auto-filling applications using your saved profile.

## Features

- **URL Scraping**: Paste any job board URL (LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, Workday, or generic sites) and press Enter to extract job listings
- **Smart Parsing**: Uses schema.org JSON-LD `JobPosting` structured data first, falls back to heuristic DOM parsing
- **Job Tracker**: Local SQLite database tracks all scraped jobs with status (New/Applied/Skipped)
- **Profile Manager**: Save your personal info, education, experience, skills, links, resume, cover letter template, and screening Q&A bank
- **Auto-Fill Engine**: Opens the real application form in a visible browser and fills fields using intelligent field matching
- **Safety First**: **Never auto-submits** — you review and click submit yourself
- **Dark Paper Theme**: Worn leather notebook aesthetic with warm sepia panels and burnt amber accents

## Tech Stack

- **Python** — Single language, no C++
- **PySide6** — Qt GUI framework (LGPL)
- **Playwright** — Browser automation for scraping and auto-fill (shared persistent session)
- **BeautifulSoup4** — HTML parsing helper
- **rapidfuzz** — Fuzzy string matching for field mapping
- **SQLite** — Local data storage (stdlib)
- **PyInstaller** — Single-file Windows executable

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/JFind.git
cd JFind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the app
python job_autofill_app/main.py
```

### Building Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build single-file executable
pyinstaller job_autofill_app.spec

# Output: dist/JFind.exe (Windows) or dist/JFind (Linux/macOS)
```

## Usage

1. **First Run**: Click "Profile" in the toolbar to enter your personal information, education, experience, skills, resume path, and screening Q&A answers
2. **Scrape Jobs**: Paste a job board URL (search results or single posting) into the URL bar and press Enter
3. **Browse Results**: Click any job card to view full details
4. **Auto-Fill**: Click "Auto-fill Application" — a browser window opens with the form pre-filled from your profile
5. **Review & Submit**: Check the filled data, fill any skipped fields manually, then click Submit yourself

## Supported Sites

| Site/ATS | Status |
|----------|--------|
| LinkedIn | ✅ Search results & detail pages |
| Indeed | ✅ Search results & detail pages |
| Glassdoor | ✅ Search results & detail pages |
| Greenhouse | ✅ Job boards & detail pages |
| Lever | ✅ Job boards & detail pages |
| Workday | ✅ Career sites (JSON-LD + embedded data) |
| Generic | ✅ JSON-LD JobPosting + heuristics |

## Project Structure

```
job_autofill_app/
├── main.py                  # Entry point
├── ui/
│   ├── main_window.py       # URL bar, results list, navigation
│   ├── profile_editor.py    # Profile form UI
│   ├── job_detail_view.py   # Job detail + auto-fill button
│   ├── theme.qss            # Dark paper stylesheet
│   └── theme.py             # Theme utilities
├── core/
│   ├── scraper.py           # Orchestrates scraping + adapter routing
│   ├── adapters/            # Site-specific adapters
│   │   ├── generic.py       # JSON-LD + heuristics
│   │   ├── linkedin.py
│   │   ├── indeed.py
│   │   ├── glassdoor.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   └── workday.py
│   ├── autofill.py          # Playwright form filler (never auto-submits)
│   ├── field_matcher.py     # Profile → form field mapping
│   └── browser_session.py   # Shared Playwright persistent context
├── data/
│   ├── db.py                # SQLite schema + CRUD
│   └── models.py            # Profile, JobListing dataclasses
├── requirements.txt
└── job_autofill_app.spec    # PyInstaller spec
```

## Safety & Ethics

- **No auto-submit**: The app fills forms but never clicks Submit
- **Session reuse**: Playwright persistent context keeps you logged in across scraping and auto-fill
- **Rate limiting**: Built-in delays between requests
- **No CAPTCHA solving**: Surfaces CAPTCHAs for manual solving
- **Local-only data**: Profile and job history stay in local SQLite — no cloud sync
- **ToS awareness**: Some sites (especially LinkedIn) restrict automated interaction — use responsibly

## License

MIT License — see [LICENSE](LICENSE) for details.