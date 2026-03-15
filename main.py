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
        QMainWindow, QDialog {
            background-color: #2d2d30;
            color: #e0e0e0;
        }
        QTableView {
            background-color: #202022;
            color: #e0e0e0;
            selection-background-color: #0078d7;
            selection-color: white;
            gridline-color: #3e3e42;
            alternate-background-color: #2a2a2d;
        }
        QPushButton {
            background-color: #ec7846;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #bf6741;
        }

        /* Mode switch buttons */
        QPushButton#all_tabs_btn, QPushButton#learned_tabs_btn {
            background-color: #333337;
            min-width: 120px;
        }
        QPushButton#all_tabs_btn:checked {
            background-color: #ff0000;
            border-bottom: 3px solid #ff5555;
        }
        QPushButton#learned_tabs_btn:checked {
            background-color: #2d5a2d;
            border-bottom: 3px solid #4CAF50;
        }
        QPushButton#all_tabs_btn:hover:!checked {
            background-color: #444448;
        }
        QPushButton#learned_tabs_btn:hover:!checked {
            background-color: #444448;
        }

        QTabWidget::pane {
            border: 1px solid #3e3e42;
        }
        QTabBar::tab {
            background-color: #333337;
            color: #e0e0e0;
            padding: 8px 16px;
        }
        QTabBar::tab:selected {
            background-color: #2d2d30;
            border-bottom: 2px solid #e89018;
        }
        QHeaderView::section {
            background-color: #3e3e42;
            color: #e0e0e0;
            padding: 6px;
            border: none;
        }
        QLabel, QComboBox, QLineEdit {
            color: #e0e0e0;
        }
        QComboBox, QLineEdit, QTextEdit, QSpinBox {
            background-color: #333337;
            color: #e0e0e0;
            border: 1px solid #3e3e42;
            padding: 4px;
        }
        QComboBox QAbstractItemView {
            background-color: #333337;
            color: #e0e0e0;
            selection-background-color: #0078d7;
        }
        QMenu {
            background-color: #2b2b2e;
            color: #e0e0e0;
            border: 1px solid #4a4a4f;
            font-family: "Segoe UI";
            font-size: 11pt;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 7px 28px 7px 16px;
        }
        QMenu::item:selected {
            background-color: #0078d7;
            border-radius: 3px;
        }
        QMenu::separator {
            height: 1px;
            background: #4a4a4f;
            margin: 4px 8px;
        }

        /* Pitch Shifter button */
        QPushButton#pitch_shifter_btn {
            background-color: #333337;
            min-width: 120px;
        }
        QPushButton#pitch_shifter_btn:hover {
            background-color: #e89018;
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
    except Exception as e:
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
