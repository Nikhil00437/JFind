"""Profile editor dialog for managing user profile data."""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QTextEdit, QPushButton, QLabel,
    QComboBox, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QGroupBox, QScrollArea, QFrame, QSplitter,
    QSizePolicy, QSpinBox
)
from PySide6.QtGui import QDesktopServices, QUrl

from job_autofill_app.data.models import Profile
from job_autofill_app.data.db import save_profile, get_profile


class EditableListWidget(QWidget):
    """A widget for managing a list of items with add/edit/delete."""

    data_changed = Signal(list)

    def __init__(self, title: str, fields: list, parent=None):
        super().__init__(parent)
        self.title = title
        self.fields = fields  # List of field names for each item
        self.items = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title_label = QLabel(self.title)
        title_label.setProperty("class", "subheading-label")
        header.addWidget(title_label)
        header.addStretch()

        add_btn = QPushButton("➕ Add")
        add_btn.setProperty("class", "secondary small")
        add_btn.clicked.connect(self.add_item)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.list_widget, 1)

        # Set initial data
        self.set_items([])

    def set_items(self, items: list):
        """Set the list items."""
        self.items = items
        self.refresh_list()

    def refresh_list(self):
        """Refresh the list widget display."""
        self.list_widget.clear()
        for i, item in enumerate(self.items):
            display_text = self.format_item(item, i)
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, i)
            self.list_widget.addItem(list_item)

    def format_item(self, item: dict, index: int) -> str:
        """Format an item for display."""
        parts = []
        for field in self.fields:
            value = item.get(field, "")
            if value:
                parts.append(f"{field.replace('_', ' ').title()}: {value}")
        return " | ".join(parts) if parts else f"Item {index + 1}"

    def add_item(self):
        """Add a new item."""
        dialog = ItemEditDialog(self.fields, {}, self)
        if dialog.exec() == QDialog.Accepted:
            self.items.append(dialog.get_data())
            self.refresh_list()
            self.data_changed.emit(self.items)

    def edit_item(self, index: int):
        """Edit an existing item."""
        if 0 <= index < len(self.items):
            dialog = ItemEditDialog(self.fields, self.items[index], self)
            if dialog.exec() == QDialog.Accepted:
                self.items[index] = dialog.get_data()
                self.refresh_list()
                self.data_changed.emit(self.items)

    def delete_item(self, index: int):
        """Delete an item."""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_list()
            self.data_changed.emit(self.items)

    def get_items(self) -> list:
        return self.items


class ItemEditDialog(QDialog):
    """Dialog for editing a single list item."""

    def __init__(self, fields: list, data: dict, parent=None):
        super().__init__(parent)
        self.fields = fields
        self.data = data.copy()
        self.setWindowTitle("Edit Item")
        self.setModal(True)
        self.resize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        self.field_widgets = {}

        for field in self.fields:
            widget = QLineEdit()
            widget.setText(self.data.get(field, ""))
            self.field_widgets[field] = widget
            form.addRow(field.replace('_', ' ').title() + ":", widget)

        layout.addLayout(form)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.accept)
        buttons.addWidget(save_btn)

        layout.addLayout(buttons)

    def get_data(self) -> dict:
        data = {}
        for field, widget in self.field_widgets.items():
            data[field] = widget.text().strip()
        return data


class SkillsEditor(QWidget):
    """Widget for editing a tag list of skills."""

    data_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.skills = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Skills")
        title.setProperty("class", "subheading-label")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("➕ Add Skill")
        add_btn.setProperty("class", "secondary small")
        add_btn.clicked.connect(self.add_skill)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # Skills list
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget, 1)

    def set_skills(self, skills: list):
        self.skills = skills
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for skill in self.skills:
            item = QListWidgetItem(skill)
            self.list_widget.addItem(item)

    def add_skill(self):
        from PySide6.QtWidgets import QInputDialog
        skill, ok = QInputDialog.getText(self, "Add Skill", "Skill name:")
        if ok and skill.strip():
            self.skills.append(skill.strip())
            self.refresh_list()
            self.data_changed.emit(self.skills)

    def show_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self.list_widget.itemAt(pos)
        if item:
            menu = QMenu(self)
            delete_action = menu.addAction("Delete")
            action = menu.exec(self.list_widget.mapToGlobal(pos))
            if action == delete_action:
                row = self.list_widget.row(item)
                self.skills.pop(row)
                self.refresh_list()
                self.data_changed.emit(self.skills)

    def get_skills(self) -> list:
        return self.skills


class QAEditor(QWidget):
    """Widget for editing the Q&A bank."""

    data_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.qa_pairs = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Screening Q&A Bank")
        title.setProperty("class", "subheading-label")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("➕ Add Q&A")
        add_btn.setProperty("class", "secondary small")
        add_btn.clicked.connect(self.add_qa)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # QA list
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget, 1)

    def set_qa(self, qa: dict):
        self.qa_pairs = qa
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for question, answer in self.qa_pairs.items():
            display = f"Q: {question[:80]}{'...' if len(question) > 80 else ''}\nA: {answer[:80]}{'...' if len(answer) > 80 else ''}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, question)
            self.list_widget.addItem(item)

    def add_qa(self):
        dialog = QAEditDialog({}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.qa_pairs[data['question']] = data['answer']
            self.refresh_list()
            self.data_changed.emit(self.qa_pairs)

    def show_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self.list_widget.itemAt(pos)
        if item:
            menu = QMenu(self)
            edit_action = menu.addAction("Edit")
            delete_action = menu.addAction("Delete")
            action = menu.exec(self.list_widget.mapToGlobal(pos))
            question = item.data(Qt.UserRole)
            if action == edit_action:
                self.edit_qa(question)
            elif action == delete_action:
                self.qa_pairs.pop(question, None)
                self.refresh_list()
                self.data_changed.emit(self.qa_pairs)

    def edit_qa(self, question: str):
        dialog = QAEditDialog({'question': question, 'answer': self.qa_pairs.get(question, '')}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            # Remove old key if question changed
            if data['question'] != question:
                self.qa_pairs.pop(question, None)
            self.qa_pairs[data['question']] = data['answer']
            self.refresh_list()
            self.data_changed.emit(self.qa_pairs)

    def get_qa(self) -> dict:
        return self.qa_pairs


class QAEditDialog(QDialog):
    """Dialog for editing a Q&A pair."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data.copy()
        self.setWindowTitle("Edit Q&A" if data.get('question') else "Add Q&A")
        self.setModal(True)
        self.resize(500, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Question
        q_label = QLabel("Question:")
        q_label.setProperty("class", "body-label")
        layout.addWidget(q_label)

        self.question_edit = QLineEdit()
        self.question_edit.setText(self.data.get('question', ''))
        self.question_edit.setPlaceholderText("e.g., 'Are you authorized to work in the US?'")
        layout.addWidget(self.question_edit)

        # Answer
        a_label = QLabel("Answer:")
        a_label.setProperty("class", "body-label")
        layout.addWidget(a_label)

        self.answer_edit = QTextEdit()
        self.answer_edit.setText(self.data.get('answer', ''))
        self.answer_edit.setPlaceholderText("Your answer to this question...")
        self.answer_edit.setMaximumHeight(150)
        layout.addWidget(self.answer_edit)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.accept)
        buttons.addWidget(save_btn)

        layout.addLayout(buttons)

    def get_data(self) -> dict:
        return {
            'question': self.question_edit.text().strip(),
            'answer': self.answer_edit.toPlainText().strip()
        }


class ProfileEditor(QDialog):
    """Main profile editor dialog."""

    profile_saved = Signal(Profile)

    def __init__(self, profile: Profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Profile Editor")
        self.setModal(True)
        self.resize(800, 700)
        self.setup_ui()
        self.load_profile()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Personal tab
        self.personal_tab = self.create_personal_tab()
        self.tabs.addTab(self.personal_tab, "Personal")

        # Links tab
        self.links_tab = self.create_links_tab()
        self.tabs.addTab(self.links_tab, "Links")

        # Education tab
        self.education_tab = self.create_education_tab()
        self.tabs.addTab(self.education_tab, "Education")

        # Experience tab
        self.experience_tab = self.create_experience_tab()
        self.tabs.addTab(self.experience_tab, "Experience")

        # Skills tab
        self.skills_tab = self.create_skills_tab()
        self.tabs.addTab(self.skills_tab, "Skills")

        # Resume tab
        self.resume_tab = self.create_resume_tab()
        self.tabs.addTab(self.resume_tab, "Resume")

        # Q&A tab
        self.qa_tab = self.create_qa_tab()
        self.tabs.addTab(self.qa_tab, "Q&A Bank")

        # Button bar
        button_bar = QFrame()
        button_bar.setFixedHeight(60)
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(20, 10, 20, 10)
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Profile")
        save_btn.setProperty("class", "primary")
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self.save_profile)
        button_layout.addWidget(save_btn)

        layout.addWidget(button_bar)

    def create_personal_tab(self) -> QWidget:
        """Create the personal information tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Name group
        name_group = QGroupBox("Name")
        name_layout = QFormLayout(name_group)
        name_layout.setSpacing(12)

        self.full_name_edit = QLineEdit()
        self.full_name_edit.setPlaceholderText("Full legal name")
        name_layout.addRow("Full Name:", self.full_name_edit)

        layout.addWidget(name_group)

        # Contact group
        contact_group = QGroupBox("Contact")
        contact_layout = QFormLayout(contact_group)
        contact_layout.setSpacing(12)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("email@example.com")
        contact_layout.addRow("Email:", self.email_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+1 (555) 123-4567")
        contact_layout.addRow("Phone:", self.phone_edit)

        layout.addWidget(contact_group)

        # Address group
        address_group = QGroupBox("Address")
        address_layout = QFormLayout(address_group)
        address_layout.setSpacing(12)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Street address")
        address_layout.addRow("Street:", self.address_edit)

        self.city_edit = QLineEdit()
        self.city_edit.setPlaceholderText("City")
        address_layout.addRow("City:", self.city_edit)

        self.state_edit = QLineEdit()
        self.state_edit.setPlaceholderText("State/Province")
        address_layout.addRow("State:", self.state_edit)

        self.country_edit = QLineEdit()
        self.country_edit.setPlaceholderText("Country")
        address_layout.addRow("Country:", self.country_edit)

        layout.addWidget(address_group)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def create_links_tab(self) -> QWidget:
        """Create the links tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        links_group = QGroupBox("Profile Links")
        links_layout = QFormLayout(links_group)
        links_layout.setSpacing(12)

        self.linkedin_edit = QLineEdit()
        self.linkedin_edit.setPlaceholderText("https://linkedin.com/in/yourname")
        links_layout.addRow("LinkedIn:", self.linkedin_edit)

        self.github_edit = QLineEdit()
        self.github_edit.setPlaceholderText("https://github.com/yourname")
        links_layout.addRow("GitHub:", self.github_edit)

        self.portfolio_edit = QLineEdit()
        self.portfolio_edit.setPlaceholderText("https://yourportfolio.com")
        links_layout.addRow("Portfolio:", self.portfolio_edit)

        self.other_edit = QLineEdit()
        self.other_edit.setPlaceholderText("Other relevant URL")
        links_layout.addRow("Other:", self.other_edit)

        layout.addWidget(links_group)
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def create_education_tab(self) -> QWidget:
        """Create the education tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        self.education_editor = EditableListWidget(
            "Education",
            ["school", "degree", "field", "start", "end", "gpa"]
        )
        self.education_editor.data_changed.connect(self.on_education_changed)
        layout.addWidget(self.education_editor)
        return widget

    def create_experience_tab(self) -> QWidget:
        """Create the experience tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        self.experience_editor = EditableListWidget(
            "Work Experience",
            ["company", "title", "start", "end", "description"]
        )
        self.experience_editor.data_changed.connect(self.on_experience_changed)
        layout.addWidget(self.experience_editor)
        return widget

    def create_skills_tab(self) -> QWidget:
        """Create the skills tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        self.skills_editor = SkillsEditor()
        self.skills_editor.data_changed.connect(self.on_skills_changed)
        layout.addWidget(self.skills_editor)
        return widget

    def create_resume_tab(self) -> QWidget:
        """Create the resume/cover letter tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Resume file
        resume_group = QGroupBox("Resume / CV")
        resume_layout = QVBoxLayout(resume_group)
        resume_layout.setSpacing(12)

        resume_row = QHBoxLayout()
        self.resume_path_edit = QLineEdit()
        self.resume_path_edit.setPlaceholderText("Path to resume PDF")
        self.resume_path_edit.setReadOnly(True)
        resume_row.addWidget(self.resume_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.setProperty("class", "secondary")
        browse_btn.clicked.connect(self.browse_resume)
        resume_row.addWidget(browse_btn)

        resume_layout.addLayout(resume_row)

        # Cover letter template
        cover_group = QGroupBox("Cover Letter Template")
        cover_layout = QVBoxLayout(cover_group)
        cover_layout.setSpacing(12)

        self.cover_letter_edit = QTextEdit()
        self.cover_letter_edit.setPlaceholderText(
            "Enter a cover letter template. Use placeholders like {{company}}, {{title}}, {{name}}..."
        )
        self.cover_letter_edit.setMinimumHeight(200)
        cover_layout.addWidget(self.cover_letter_edit)

        layout.addWidget(resume_group)
        layout.addWidget(cover_group)
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def create_qa_tab(self) -> QWidget:
        """Create the Q&A bank tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        self.qa_editor = QAEditor()
        self.qa_editor.data_changed.connect(self.on_qa_changed)
        layout.addWidget(self.qa_editor)
        return widget

    def load_profile(self):
        """Load profile data into the form."""
        self.full_name_edit.setText(self.profile.full_name)
        self.email_edit.setText(self.profile.email)
        self.phone_edit.setText(self.profile.phone)
        self.address_edit.setText(self.profile.address)
        self.city_edit.setText(self.profile.city)
        self.state_edit.setText(self.profile.state)
        self.country_edit.setText(self.profile.country)

        self.linkedin_edit.setText(self.profile.links.get("linkedin", ""))
        self.github_edit.setText(self.profile.links.get("github", ""))
        self.portfolio_edit.setText(self.profile.links.get("portfolio", ""))
        self.other_edit.setText(self.profile.links.get("other", ""))

        self.education_editor.set_items(self.profile.education)
        self.experience_editor.set_items(self.profile.experience)
        self.skills_editor.set_skills(self.profile.skills)

        self.resume_path_edit.setText(self.profile.resume_path)
        self.cover_letter_edit.setPlainText(self.profile.cover_letter_template)

        self.qa_editor.set_qa(self.profile.qa_bank)

    def browse_resume(self):
        """Browse for resume file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Resume", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.resume_path_edit.setText(file_path)

    def on_education_changed(self, items: list):
        self.profile.education = items

    def on_experience_changed(self, items: list):
        self.profile.experience = items

    def on_skills_changed(self, skills: list):
        self.profile.skills = skills

    def on_qa_changed(self, qa: dict):
        self.profile.qa_bank = qa

    def save_profile(self):
        """Save the profile to database."""
        # Collect all data
        self.profile.full_name = self.full_name_edit.text().strip()
        self.profile.email = self.email_edit.text().strip()
        self.profile.phone = self.phone_edit.text().strip()
        self.profile.address = self.address_edit.text().strip()
        self.profile.city = self.city_edit.text().strip()
        self.profile.state = self.state_edit.text().strip()
        self.profile.country = self.country_edit.text().strip()

        self.profile.links = {
            "linkedin": self.linkedin_edit.text().strip(),
            "github": self.github_edit.text().strip(),
            "portfolio": self.portfolio_edit.text().strip(),
            "other": self.other_edit.text().strip(),
        }

        self.profile.resume_path = self.resume_path_edit.text().strip()
        self.profile.cover_letter_template = self.cover_letter_edit.toPlainText().strip()

        # Save to database
        saved_profile = save_profile(self.profile)
        self.profile = saved_profile
        self.profile_saved.emit(saved_profile)
        self.accept()


def run_profile_editor(parent=None) -> Optional[Profile]:
    """Run the profile editor and return the saved profile."""
    profile = get_profile()
    editor = ProfileEditor(profile, parent)
    if editor.exec() == QDialog.Accepted:
        return editor.profile
    return None