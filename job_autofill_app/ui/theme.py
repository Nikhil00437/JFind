"""Theme application utilities."""

from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtCore import QFile, QTextStream


def load_fonts():
    """Load custom fonts if available."""
    # Try to load Crimson Pro if available
    font_paths = [
        Path(__file__).parent / "assets" / "fonts" / "CrimsonPro-Regular.ttf",
        Path(__file__).parent / "assets" / "fonts" / "CrimsonPro-Bold.ttf",
        Path(__file__).parent / "assets" / "fonts" / "CrimsonPro-SemiBold.ttf",
    ]
    
    for font_path in font_paths:
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


def apply_theme(widget: QWidget):
    """Apply the dark paper theme to a widget."""
    # Load custom fonts
    load_fonts()

    # Set default font
    default_font = QFont("Segoe UI", 13)
    default_font.setHintingPreference(QFont.PreferFullHinting)
    widget.setFont(default_font)

    # Load and apply QSS stylesheet
    qss_path = Path(__file__).parent / "theme.qss"
    if qss_path.exists():
        with open(qss_path, "r") as f:
            stylesheet = f.read()
        widget.setStyleSheet(stylesheet)
    else:
        # Fallback inline styles
        widget.setStyleSheet("""
            QWidget {
                background-color: #1a1714;
                color: #e8dfd0;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 13px;
            }
        """)


def get_paper_stylesheet() -> str:
    """Get the paper theme stylesheet as a string."""
    qss_path = Path(__file__).parent / "theme.qss"
    if qss_path.exists():
        with open(qss_path, "r") as f:
            return f.read()
    return ""


def setup_application(app: QApplication):
    """Set up application-wide theme and settings."""
    # Load fonts
    load_fonts()

    # Set application font
    font = QFont("Segoe UI", 13)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    # Apply stylesheet
    qss_path = Path(__file__).parent / "theme.qss"
    if qss_path.exists():
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())

    # Set style hint for better rendering
    app.setStyle("Fusion")