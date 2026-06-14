import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer
from guitar_tabs_app import GuitarTabApp  # Fixed: was GuitarTabsApp


def resource_path(relative):
    """Return correct path whether running as script or frozen .exe."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def main():
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    app.setStyleSheet("""
        /* ── Base ─────────────────────────────────────────── */
        QMainWindow, QDialog, QWidget {
            background-color: #1e1e22;
            color: #e0e0e0;
            font-family: "Segoe UI", Arial, sans-serif;
        }

        /* ── Buttons (default – neutral) ──────────────────── */
        QPushButton {
            background-color: #2e2e34;
            color: #cccccc;
            border: 1px solid #3a3a42;
            padding: 6px 14px;
            border-radius: 4px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #3a3a42;
            color: #ffffff;
            border-color: #555560;
        }
        QPushButton:pressed  { background-color: #26262c; }
        QPushButton:disabled { color: #555558; border-color: #2e2e34; }

        /* ── Table ────────────────────────────────────────── */
        QTableView {
            background-color: #1e1e22;
            color: #e0e0e0;
            selection-background-color: #2c3e5a;
            selection-color: #ffffff;
            gridline-color: #2a2a30;
            alternate-background-color: #232328;
            border: none;
            outline: none;
        }
        QTableView::item:hover { background-color: #28282e; }
        QTableView::item:selected { background-color: #2c3e5a; color: #ffffff; }

        /* ── Tab widget ───────────────────────────────────── */
        QTabWidget::pane  { border: none; background-color: #1e1e22; }
        QTabBar           { background: transparent; }
        QTabBar::tab {
            background: transparent;
            color: #777777;
            padding: 8px 16px;
            border: none;
            border-bottom: 2px solid transparent;
            margin-right: 2px;
            font-size: 12px;
        }
        QTabBar::tab:selected        { color: #e3ac63; border-bottom: 2px solid #e3ac63; }
        QTabBar::tab:hover:!selected { color: #cccccc; border-bottom: 2px solid #444448; }

        /* ── Header ───────────────────────────────────────── */
        QHeaderView::section {
            background-color: #252528;
            color: #999999;
            padding: 5px 8px;
            border: none;
            border-bottom: 1px solid #333338;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        QHeaderView::section:hover { background-color: #2e2e34; color: #e3ac63; }

        /* ── Inputs ───────────────────────────────────────── */
        QLabel  { color: #cccccc; }
        QLineEdit, QTextEdit, QSpinBox {
            background-color: #28282e;
            color: #e0e0e0;
            border: 1px solid #3a3a42;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus { border-color: #e3ac63; }
        QComboBox {
            background-color: #28282e;
            color: #e0e0e0;
            border: 1px solid #3a3a42;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QComboBox:focus { border-color: #e3ac63; }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView {
            background-color: #28282e;
            color: #e0e0e0;
            selection-background-color: #e3ac63;
            selection-color: #1e1e22;
            border: 1px solid #3a3a42;
            outline: none;
        }

        /* ── Menu ─────────────────────────────────────────── */
        QMenu {
            background-color: #28282e;
            color: #e0e0e0;
            border: 1px solid #3a3a42;
            padding: 4px 0px;
        }
        QMenu::item          { padding: 7px 28px 7px 16px; }
        QMenu::item:selected { background-color: #2c3e5a; color: #ffffff; }
        QMenu::separator     { height: 1px; background: #3a3a42; margin: 4px 8px; }

        /* ── Status bar ───────────────────────────────────── */
        QStatusBar {
            background-color: #17171b;
            color: #777777;
            border-top: 1px solid #2a2a30;
            font-size: 11px;
        }

        /* ── Scrollbars ───────────────────────────────────── */
        QScrollBar:vertical   { background: #1e1e22; width: 8px; border: none; margin: 0; }
        QScrollBar:horizontal { background: #1e1e22; height: 8px; border: none; margin: 0; }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #3a3a42;
            border-radius: 4px;
            min-height: 24px;
            min-width: 24px;
        }
        QScrollBar::handle:vertical:hover,
        QScrollBar::handle:horizontal:hover { background: #555560; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical   { height: 0; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

        /* ── Progress bar ─────────────────────────────────── */
        QProgressBar {
            background-color: #28282e;
            border: 1px solid #3a3a42;
            border-radius: 3px;
            text-align: center;
            color: #e0e0e0;
            height: 14px;
        }
        QProgressBar::chunk { background-color: #e3ac63; border-radius: 3px; }

        /* ── Checkbox ─────────────────────────────────────── */
        QCheckBox { color: #cccccc; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #3a3a42;
            border-radius: 3px;
            background: #28282e;
        }
        QCheckBox::indicator:checked { background: #e3ac63; border-color: #e3ac63; }

        /* ── GroupBox ─────────────────────────────────────── */
        QGroupBox {
            color: #aaaaaa;
            border: 1px solid #3a3a42;
            border-radius: 4px;
            padding-top: 12px;
            margin-top: 6px;
            font-weight: bold;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #aaaaaa; }

        /* ── Tooltip ──────────────────────────────────────── */
        QToolTip {
            background-color: #2a2a30;
            color: #e0e0e0;
            border: 1px solid #444450;
            padding: 4px 8px;
        }
    """)

    try:
        # Splash screen — shown for 3 seconds before the main window appears
        splash_pix = QPixmap(resource_path("logo.png"))
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setWindowFlag(Qt.FramelessWindowHint)
        splash.show()
        app.processEvents()

        window = GuitarTabApp()

        # Set object names for styling
        window.all_tabs_btn.setObjectName("all_tabs_btn")
        window.learned_tabs_btn.setObjectName("learned_tabs_btn")
        window.pitch_shifter_btn.setObjectName("pitch_shifter_btn")

        QTimer.singleShot(3000, lambda: (splash.finish(window), window.show()))
        sys.exit(app.exec_())
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
