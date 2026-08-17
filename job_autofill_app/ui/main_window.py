"""Main application window with URL bar, results list, and navigation."""

import sys
from typing import List, Optional
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QSize, QRect
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QSplitter,
    QFrame, QScrollArea, QStackedWidget, QMessageBox, QMenu,
    QStatusBar, QToolBar, QStyle, QApplication, QSizePolicy
)
from PySide6.QtGui import QIcon, QPixmap, QFont, QCursor, QAction

from job_autofill_app.data.models import JobListing
from job_autofill_app.data.db import (
    init_db, get_all_job_listings, save_job_listing,
    update_job_status, delete_job_listing
)
from job_autofill_app.core.scraper import scrape_url
from job_autofill_app.ui.job_detail_view import JobDetailView
from job_autofill_app.ui.profile_editor import ProfileEditor
from job_autofill_app.ui.theme import apply_theme


class ScraperWorker(QThread):
    """Background worker for scraping job listings."""
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, url: str, headless: bool = True):
        super().__init__()
        self.url = url
        self.headless = headless

    def run(self):
        import asyncio
        try:
            self.progress.emit("Loading page...")
            jobs = asyncio.run(scrape_url(self.url, headless=self.headless))
            self.finished.emit(jobs)
        except Exception as e:
            self.error.emit(str(e))


class JobCardWidget(QFrame):
    """Individual job card widget for the results list."""

    clicked = Signal(JobListing)
    auto_fill_requested = Signal(JobListing)

    def __init__(self, job: JobListing, parent=None):
        super().__init__(parent)
        self.job = job
        self.setObjectName("jobCard")
        self.setProperty("class", "paper-card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(140)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Top row: Title and status badge
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        self.title_label = QLabel(self.job.title)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setProperty("class", "heading-label")
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_layout.addWidget(self.title_label)

        # Status badge
        self.status_label = QLabel(self.job.status)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFixedHeight(24)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(self._status_style(self.job.status))
        top_layout.addWidget(self.status_label)

        layout.addLayout(top_layout)

        # Company and location
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        company_text = self.job.company or "Unknown Company"
        self.company_label = QLabel(company_text)
        self.company_label.setObjectName("companyLabel")
        self.company_label.setProperty("class", "muted-label")
        meta_layout.addWidget(self.company_label)

        if self.job.location:
            self.location_label = QLabel(self.job.location)
            self.location_label.setObjectName("locationLabel")
            self.location_label.setProperty("class", "muted-label")
            meta_layout.addWidget(self.location_label)

        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Description snippet
        if self.job.description:
            snippet = self.job.description[:200] + "..." if len(self.job.description) > 200 else self.job.description
            self.snippet_label = QLabel(snippet)
            self.snippet_label.setObjectName("snippetLabel")
            self.snippet_label.setProperty("class", "body-label")
            self.snippet_label.setWordWrap(True)
            layout.addWidget(self.snippet_label)

        # Bottom row: salary and auto-fill button
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        if self.job.salary:
            self.salary_label = QLabel(self.job.salary)
            self.salary_label.setObjectName("salaryLabel")
            self.salary_label.setProperty("class", "dim-label")
            bottom_layout.addWidget(self.salary_label)

        bottom_layout.addStretch()

        # Auto-fill button
        self.auto_fill_btn = QPushButton("Auto-fill")
        self.auto_fill_btn.setObjectName("autoFillBtn")
        self.auto_fill_btn.setProperty("class", "primary small")
        self.auto_fill_btn.setFixedWidth(100)
        self.auto_fill_btn.clicked.connect(lambda: self.auto_fill_requested.emit(self.job))
        bottom_layout.addWidget(self.auto_fill_btn)

        # View details button
        self.view_btn = QPushButton("View")
        self.view_btn.setObjectName("viewBtn")
        self.view_btn.setProperty("class", "secondary small")
        self.view_btn.setFixedWidth(70)
        self.view_btn.clicked.connect(lambda: self.clicked.emit(self.job))
        bottom_layout.addWidget(self.view_btn)

        layout.addLayout(bottom_layout)

    def _status_style(self, status: str) -> str:
        styles = {
            "New": "background-color: #a8613a; color: #1a1714; border-radius: 12px; padding: 0 12px; font-weight: 600; font-size: 11px;",
            "Applied": "background-color: #5a7a4a; color: #e8dfd0; border-radius: 12px; padding: 0 12px; font-weight: 600; font-size: 11px;",
            "Skipped": "background-color: #3d3328; color: #7a6f5e; border-radius: 12px; padding: 0 12px; font-weight: 600; font-size: 11px;",
        }
        return styles.get(status, styles["New"])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.job)
        super().mousePressEvent(event)

    def update_job(self, job: JobListing):
        self.job = job
        self.title_label.setText(job.title)
        self.company_label.setText(job.company or "Unknown Company")
        self.status_label.setText(job.status)
        self.status_label.setStyleSheet(self._status_style(job.status))
        if hasattr(self, 'location_label'):
            self.location_label.setText(job.location)
        if hasattr(self, 'snippet_label'):
            snippet = job.description[:200] + "..." if len(job.description) > 200 else job.description
            self.snippet_label.setText(snippet)
        if hasattr(self, 'salary_label'):
            self.salary_label.setText(job.salary or "")


class ResultsListWidget(QListWidget):
    """Custom list widget for job results with card-based layout."""

    job_selected = Signal(JobListing)
    auto_fill_requested = Signal(JobListing)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resultsList")
        self.setSpacing(12)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("""
            QListWidget#resultsList {
                background-color: transparent;
                border: none;
            }
            QListWidget#resultsList::item {
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)

    def add_job(self, job: JobListing):
        """Add a job listing to the results list."""
        item = QListWidgetItem()
        card = JobCardWidget(job)
        card.clicked.connect(self.job_selected.emit)
        card.auto_fill_requested.connect(self.auto_fill_requested.emit)
        
        item.setSizeHint(card.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, card)

    def clear_jobs(self):
        """Clear all jobs from the list."""
        self.clear()

    def update_job(self, job: JobListing):
        """Update a specific job in the list."""
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if isinstance(widget, JobCardWidget) and widget.job.id == job.id:
                widget.update_job(job)
                break


class LoadingOverlay(QWidget):
    """Overlay widget showing loading state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.spinner_label = QLabel("🔍")
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(self.spinner_label)

        self.text_label = QLabel("Scraping job listings...")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setProperty("class", "muted-label")
        self.text_label.setStyleSheet("font-size: 16px; margin-top: 16px;")
        layout.addWidget(self.text_label)

        self.setStyleSheet("""
            QWidget#loadingOverlay {
                background-color: rgba(26, 23, 20, 0.9);
                border-radius: 12px;
            }
        """)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JFind — Job Scraper & Auto-Fill")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self.current_jobs: List[JobListing] = []
        self.scraper_worker: Optional[ScraperWorker] = None

        self.setup_ui()
        self.apply_styles()
        self.load_saved_jobs()

    def setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar area
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbarFrame")
        toolbar_frame.setFixedHeight(60)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(20, 8, 20, 8)
        toolbar_layout.setSpacing(16)

        # App title
        title_label = QLabel("JFind")
        title_label.setProperty("class", "heading-label")
        title_label.setStyleSheet("font-size: 24px;")
        toolbar_layout.addWidget(title_label)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("urlBar")
        self.url_bar.setPlaceholderText("Paste a job page URL and press Enter…")
        self.url_bar.setMinimumWidth(400)
        self.url_bar.returnPressed.connect(self.on_scrape_requested)
        toolbar_layout.addWidget(self.url_bar, 1)

        # Headless toggle
        self.headless_toggle = QPushButton("Headless")
        self.headless_toggle.setCheckable(True)
        self.headless_toggle.setChecked(True)
        self.headless_toggle.setProperty("class", "secondary small")
        self.headless_toggle.setToolTip("Toggle headless browser mode")
        toolbar_layout.addWidget(self.headless_toggle)

        # Profile button
        self.profile_btn = QPushButton("Profile")
        self.profile_btn.setProperty("class", "secondary")
        self.profile_btn.clicked.connect(self.show_profile_editor)
        toolbar_layout.addWidget(self.profile_btn)

        main_layout.addWidget(toolbar_frame)

        # Main content splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        main_layout.addWidget(self.splitter, 1)

        # Left panel: Results list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 8, 16)
        left_layout.setSpacing(12)

        # Results header
        results_header = QHBoxLayout()
        self.results_title = QLabel("Job Listings")
        self.results_title.setProperty("class", "subheading-label")
        results_header.addWidget(self.results_title)

        self.results_count = QLabel("")
        self.results_count.setProperty("class", "dim-label")
        results_header.addWidget(self.results_count)

        results_header.addStretch()

        # Filter controls
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "New", "Applied", "Skipped"])
        self.status_filter.setFixedWidth(100)
        self.status_filter.currentTextChanged.connect(self.filter_jobs)
        results_header.addWidget(self.status_filter)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedWidth(150)
        self.search_box.textChanged.connect(self.filter_jobs)
        results_header.addWidget(self.search_box)

        left_layout.addLayout(results_header)

        # Results list
        self.results_list = ResultsListWidget()
        self.results_list.job_selected.connect(self.show_job_detail)
        self.results_list.auto_fill_requested.connect(self.on_auto_fill_requested)
        left_layout.addWidget(self.results_list, 1)

        # Loading overlay
        self.loading_overlay = LoadingOverlay(self.results_list)
        self.loading_overlay.resize(self.results_list.size())

        self.splitter.addWidget(left_panel)

        # Right panel: Stacked widget for detail view / empty state
        self.right_stack = QStackedWidget()
        self.splitter.addWidget(self.right_stack)

        # Empty state
        self.empty_state = self.create_empty_state()
        self.right_stack.addWidget(self.empty_state)

        # Job detail view (created on demand)
        self.detail_view = None

        # Set splitter sizes (60/40)
        self.splitter.setSizes([720, 480])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def create_empty_state(self) -> QWidget:
        """Create the empty state widget."""
        widget = QWidget()
        widget.setObjectName("emptyState")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        icon_label = QLabel("📄")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px;")
        layout.addWidget(icon_label)

        title = QLabel("No job selected")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("class", "heading-label")
        title.setStyleSheet("font-size: 20px;")
        layout.addWidget(title)

        desc = QLabel("Paste a job board URL above and press Enter to scrape listings.\nThen click a listing to view details or auto-fill the application.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setProperty("class", "muted-label")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.6;")
        layout.addWidget(desc)

        return widget

    def apply_styles(self):
        apply_theme(self)

    def load_saved_jobs(self):
        """Load previously saved jobs from database."""
        init_db()
        jobs = get_all_job_listings()
        self.current_jobs = jobs
        self.populate_results_list(jobs)
        self.update_results_count()

    def populate_results_list(self, jobs: List[JobListing]):
        """Populate the results list with jobs."""
        self.results_list.clear_jobs()
        for job in jobs:
            self.results_list.add_job(job)

    def filter_jobs(self):
        """Filter jobs based on status and search query."""
        status = self.status_filter.currentText()
        query = self.search_box.text().strip()

        jobs = get_all_job_listings(
            status_filter=status if status != "All" else None,
            search_query=query
        )
        self.current_jobs = jobs
        self.populate_results_list(jobs)
        self.update_results_count()

    def update_results_count(self):
        """Update the results count label."""
        count = len(self.current_jobs)
        self.results_count.setText(f"{count} listing{'s' if count != 1 else ''}")

    def on_scrape_requested(self):
        """Handle URL bar enter press - start scraping."""
        url = self.url_bar.text().strip()
        if not url:
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_bar.setText(url)

        self.start_scraping(url)

    def start_scraping(self, url: str):
        """Start the scraping worker."""
        # Show loading state
        self.loading_overlay.resize(self.results_list.size())
        self.loading_overlay.show()
        self.results_list.setEnabled(False)
        self.url_bar.setEnabled(False)
        self.status_bar.showMessage(f"Scraping {url}...")

        # Start worker
        headless = self.headless_toggle.isChecked()
        self.scraper_worker = ScraperWorker(url, headless=headless)
        self.scraper_worker.finished.connect(self.on_scraping_finished)
        self.scraper_worker.error.connect(self.on_scraping_error)
        self.scraper_worker.progress.connect(self.on_scraping_progress)
        self.scraper_worker.start()

    def on_scraping_progress(self, message: str):
        """Handle scraping progress updates."""
        self.status_bar.showMessage(message)
        self.loading_overlay.text_label.setText(message)

    def on_scraping_finished(self, jobs: List[JobListing]):
        """Handle scraping completion."""
        self.loading_overlay.hide()
        self.results_list.setEnabled(True)
        self.url_bar.setEnabled(True)

        if not jobs:
            self.status_bar.showMessage("No job listings found on this page")
            QMessageBox.information(self, "No Results", 
                "No job listings could be extracted from this page.\n"
                "The page might use a format not yet supported, or require login.")
            return

        # Save jobs to database
        for job in jobs:
            save_job_listing(job)

        # Refresh the list
        self.filter_jobs()
        self.status_bar.showMessage(f"Found {len(jobs)} job listing{'s' if len(jobs) != 1 else ''}")

    def on_scraping_error(self, error: str):
        """Handle scraping error."""
        self.loading_overlay.hide()
        self.results_list.setEnabled(True)
        self.url_bar.setEnabled(True)
        self.status_bar.showMessage("Scraping failed")
        QMessageBox.critical(self, "Scraping Error", f"Failed to scrape the page:\n\n{error}")

    def show_job_detail(self, job: JobListing):
        """Show the job detail view."""
        if self.detail_view is None:
            self.detail_view = JobDetailView()
            self.detail_view.auto_fill_requested.connect(self.on_auto_fill_requested)
            self.detail_view.status_changed.connect(self.on_job_status_changed)
            self.right_stack.addWidget(self.detail_view)

        self.detail_view.set_job(job)
        self.right_stack.setCurrentWidget(self.detail_view)

    def on_auto_fill_requested(self, job: JobListing):
        """Handle auto-fill request."""
        # This will be implemented when we connect to the autofill engine
        self.status_bar.showMessage(f"Opening auto-fill for: {job.title}")
        # For now, just open the apply URL in browser
        import webbrowser
        webbrowser.open(job.apply_url or job.source_url)

    def on_job_status_changed(self, job_id: int, status: str):
        """Handle job status change from detail view."""
        update_job_status(job_id, status)
        self.filter_jobs()

    def show_profile_editor(self):
        """Show the profile editor dialog."""
        from job_autofill_app.data.db import get_profile
        profile = get_profile()
        editor = ProfileEditor(profile, self)
        editor.profile_saved.connect(self.on_profile_saved)
        editor.exec()

    def on_profile_saved(self, profile):
        """Handle profile saved."""
        self.status_bar.showMessage("Profile saved", 3000)

    def resizeEvent(self, event):
        """Handle resize to update loading overlay."""
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.results_list.size())

    def closeEvent(self, event):
        """Handle window close."""
        if self.scraper_worker and self.scraper_worker.isRunning():
            self.scraper_worker.terminate()
            self.scraper_worker.wait()
        event.accept()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("JFind")
    app.setApplicationDisplayName("JFind — Job Scraper & Auto-Fill")
    app.setOrganizationName("JFind")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())