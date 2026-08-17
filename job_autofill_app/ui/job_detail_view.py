"""Job detail view with full description and auto-fill action."""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextBrowser, QSizePolicy, QSpacerItem
)
from PySide6.QtGui import QDesktopServices, QFont

from job_autofill_app.data.models import JobListing
from job_autofill_app.data.db import update_job_status


class JobDetailView(QWidget):
    """Detailed view of a single job listing."""

    auto_fill_requested = Signal(JobListing)
    status_changed = Signal(int, str)  # job_id, new_status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_job: Optional[JobListing] = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setObjectName("detailContent")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(20)

        # Header section
        self.header_frame = self.create_header()
        self.content_layout.addWidget(self.header_frame)

        # Description section
        self.desc_frame = self.create_description_section()
        self.content_layout.addWidget(self.desc_frame)

        # Meta information section
        self.meta_frame = self.create_meta_section()
        self.content_layout.addWidget(self.meta_frame)

        # Action buttons
        self.actions_frame = self.create_actions()
        self.content_layout.addWidget(self.actions_frame)

        # Status selector
        self.status_frame = self.create_status_selector()
        self.content_layout.addWidget(self.status_frame)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def create_header(self) -> QFrame:
        """Create the job header with title, company, location."""
        frame = QFrame()
        frame.setObjectName("detailHeader")
        frame.setProperty("class", "paper-panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        self.title_label = QLabel()
        self.title_label.setObjectName("detailTitle")
        self.title_label.setProperty("class", "heading-label")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 24px; line-height: 1.3;")
        layout.addWidget(self.title_label)

        # Company and location row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        self.company_label = QLabel()
        self.company_label.setObjectName("detailCompany")
        self.company_label.setProperty("class", "muted-label")
        self.company_label.setStyleSheet("font-size: 14px;")
        meta_layout.addWidget(self.company_label)

        self.location_label = QLabel()
        self.location_label.setObjectName("detailLocation")
        self.location_label.setProperty("class", "muted-label")
        self.location_label.setStyleSheet("font-size: 14px;")
        meta_layout.addWidget(self.location_label)

        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Salary if available
        self.salary_label = QLabel()
        self.salary_label.setObjectName("detailSalary")
        self.salary_label.setProperty("class", "dim-label")
        self.salary_label.setStyleSheet("font-size: 13px;")
        self.salary_label.hide()
        layout.addWidget(self.salary_label)

        return frame

    def create_description_section(self) -> QFrame:
        """Create the job description section."""
        frame = QFrame()
        frame.setObjectName("detailDescription")
        frame.setProperty("class", "paper-panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Section title
        section_title = QLabel("Description")
        section_title.setProperty("class", "subheading-label")
        section_title.setStyleSheet("font-size: 16px; border-bottom: 1px solid #3d3328; padding-bottom: 8px;")
        layout.addWidget(section_title)

        # Description text browser
        self.description_browser = QTextBrowser()
        self.description_browser.setObjectName("detailDescriptionBrowser")
        self.description_browser.setOpenExternalLinks(True)
        self.description_browser.setFrameShape(QFrame.NoFrame)
        self.description_browser.setStyleSheet("""
            QTextBrowser#detailDescriptionBrowser {
                background-color: transparent;
                border: none;
                color: #e8dfd0;
                font-size: 13px;
                line-height: 1.7;
            }
            QTextBrowser#detailDescriptionBrowser a {
                color: #a8613a;
                text-decoration: none;
            }
            QTextBrowser#detailDescriptionBrowser a:hover {
                text-decoration: underline;
            }
        """)
        self.description_browser.setMinimumHeight(200)
        layout.addWidget(self.description_browser)

        return frame

    def create_meta_section(self) -> QFrame:
        """Create the meta information section."""
        frame = QFrame()
        frame.setObjectName("detailMeta")
        frame.setProperty("class", "paper-panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        section_title = QLabel("Details")
        section_title.setProperty("class", "subheading-label")
        section_title.setStyleSheet("font-size: 16px; border-bottom: 1px solid #3d3328; padding-bottom: 8px;")
        layout.addWidget(section_title)

        # Grid of meta fields
        self.meta_grid = QVBoxLayout()
        self.meta_grid.setSpacing(8)

        self.employment_type_row = self.create_meta_row("Employment Type", "")
        self.meta_grid.addLayout(self.employment_type_row)

        self.source_url_row = self.create_meta_row("Source", "", is_link=True)
        self.meta_grid.addLayout(self.source_url_row)

        self.apply_url_row = self.create_meta_row("Apply URL", "", is_link=True)
        self.meta_grid.addLayout(self.apply_url_row)

        self.date_scraped_row = self.create_meta_row("Scraped", "")
        self.meta_grid.addLayout(self.date_scraped_row)

        layout.addLayout(self.meta_grid)

        return frame

    def create_meta_row(self, label: str, value: str, is_link: bool = False) -> QHBoxLayout:
        """Create a meta information row."""
        row = QHBoxLayout()
        row.setSpacing(12)

        label_widget = QLabel(label)
        label_widget.setProperty("class", "muted-label")
        label_widget.setFixedWidth(120)
        label_widget.setStyleSheet("font-size: 13px;")
        row.addWidget(label_widget)

        if is_link:
            value_widget = QLabel()
            value_widget.setObjectName(f"meta_{label.lower().replace(' ', '_')}")
            value_widget.setProperty("class", "link-label")
            value_widget.setStyleSheet("font-size: 13px;")
            value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
            value_widget.setOpenExternalLinks(True)
            value_widget.setWordWrap(True)
        else:
            value_widget = QLabel(value)
            value_widget.setObjectName(f"meta_{label.lower().replace(' ', '_')}")
            value_widget.setProperty("class", "body-label")
            value_widget.setStyleSheet("font-size: 13px;")
            value_widget.setWordWrap(True)

        row.addWidget(value_widget, 1)
        return row

    def create_actions(self) -> QFrame:
        """Create the action buttons."""
        frame = QFrame()
        frame.setObjectName("detailActions")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        # Auto-fill button (primary)
        self.auto_fill_btn = QPushButton("🤖 Auto-fill Application")
        self.auto_fill_btn.setObjectName("detailAutoFillBtn")
        self.auto_fill_btn.setProperty("class", "primary")
        self.auto_fill_btn.setMinimumHeight(44)
        self.auto_fill_btn.setStyleSheet("font-size: 14px; font-weight: 600; padding: 12px 24px;")
        self.auto_fill_btn.clicked.connect(self.on_auto_fill_clicked)
        layout.addWidget(self.auto_fill_btn, 1)

        # Open in browser button
        self.open_browser_btn = QPushButton("🌐 Open in Browser")
        self.open_browser_btn.setObjectName("detailOpenBrowserBtn")
        self.open_browser_btn.setProperty("class", "secondary")
        self.open_browser_btn.setMinimumHeight(44)
        self.open_browser_btn.clicked.connect(self.on_open_browser_clicked)
        layout.addWidget(self.open_browser_btn)

        return frame

    def create_status_selector(self) -> QFrame:
        """Create the job status selector."""
        frame = QFrame()
        frame.setObjectName("detailStatus")
        frame.setProperty("class", "paper-panel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        label = QLabel("Status:")
        label.setProperty("class", "muted-label")
        label.setStyleSheet("font-size: 13px;")
        layout.addWidget(label)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["New", "Applied", "Skipped"])
        self.status_combo.setFixedWidth(150)
        self.status_combo.currentTextChanged.connect(self.on_status_changed)
        layout.addWidget(self.status_combo)

        layout.addStretch()

        # Delete button
        self.delete_btn = QPushButton("🗑 Remove")
        self.delete_btn.setObjectName("detailDeleteBtn")
        self.delete_btn.setProperty("class", "danger small")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        layout.addWidget(self.delete_btn)

        return frame

    def set_job(self, job: JobListing):
        """Set the current job and update UI."""
        self.current_job = job

        # Update header
        self.title_label.setText(job.title)
        self.company_label.setText(job.company or "Unknown Company")
        self.location_label.setText(job.location or "Location not specified")

        if job.salary:
            self.salary_label.setText(f"💰 {job.salary}")
            self.salary_label.show()
        else:
            self.salary_label.hide()

        # Update description
        if job.description:
            # Convert plain text to HTML with basic formatting
            html = job.description.replace("\n\n", "</p><p>").replace("\n", "<br>")
            html = f"<p>{html}</p>"
            self.description_browser.setHtml(html)
        else:
            self.description_browser.setHtml("<p><i>No description available</i></p>")

        # Update meta fields
        self.employment_type_row.itemAt(1).widget().setText(job.employment_type or "Not specified")

        source_text = f'<a href="{job.source_url}">{job.source_url}</a>' if job.source_url else "N/A"
        self.source_url_row.itemAt(1).widget().setText(source_text)

        apply_text = f'<a href="{job.apply_url}">{job.apply_url}</a>' if job.apply_url else "N/A"
        self.apply_url_row.itemAt(1).widget().setText(apply_text)

        # Format date
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(job.date_scraped.replace('Z', '+00:00'))
            date_str = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            date_str = job.date_scraped
        self.date_scraped_row.itemAt(1).widget().setText(date_str)

        # Update status
        self.status_combo.blockSignals(True)
        self.status_combo.setCurrentText(job.status)
        self.status_combo.blockSignals(False)

    def on_auto_fill_clicked(self):
        """Handle auto-fill button click."""
        if self.current_job:
            self.auto_fill_requested.emit(self.current_job)

    def on_open_browser_clicked(self):
        """Handle open in browser button click."""
        if self.current_job:
            url = self.current_job.apply_url or self.current_job.source_url
            QDesktopServices.openUrl(QUrl(url))

    def on_status_changed(self, status: str):
        """Handle status change."""
        if self.current_job:
            update_job_status(self.current_job.id, status)
            self.current_job.status = status
            self.status_changed.emit(self.current_job.id, status)

    def on_delete_clicked(self):
        """Handle delete button click."""
        if self.current_job:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Remove Job",
                f"Remove '{self.current_job.title}' from your job tracker?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                from job_autofill_app.data.db import delete_job_listing
                delete_job_listing(self.current_job.id)
                self.status_changed.emit(self.current_job.id, "Deleted")
                # Navigate back to empty state
                parent = self.parent()
                while parent and not hasattr(parent, 'right_stack'):
                    parent = parent.parent()
                if parent and hasattr(parent, 'right_stack'):
                    parent.right_stack.setCurrentIndex(0)