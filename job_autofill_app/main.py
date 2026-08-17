"""JFind - Job Scraper & Auto-Fill Desktop Application

A dark-themed desktop app for scraping job listings and auto-filling applications.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from job_autofill_app.ui.theme import setup_application
from job_autofill_app.ui.main_window import MainWindow
from job_autofill_app.data.db import init_db


def main():
    """Application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("JFind")
    app.setApplicationDisplayName("JFind — Job Scraper & Auto-Fill")
    app.setOrganizationName("JFind")
    app.setOrganizationDomain("jfind.app")

    # Initialize database
    init_db()

    # Apply theme
    setup_application(app)

    # Create and show main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())