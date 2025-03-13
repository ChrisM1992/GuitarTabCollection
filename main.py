import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from guitar_tabs_app import GuitarTabsApp

def main():
    app = QApplication(sys.argv)

    # Set application style to Fusion for a modern look
    app.setStyle("Fusion")

    # Apply a stylesheet for additional styling
    app.setStyleSheet("""
        QMainWindow {
            background-color: white;
        }
        QTableView {
            selection-background-color: #b3d9ff;
            selection-color: black;
            gridline-color: #d9d9d9;
        }
        QPushButton {
            background-color: #8a2be2;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #9932cc;
        }
        QTabWidget::pane {
            border: 1px solid #d9d9d9;
        }
        QTabBar::tab {
            background-color: #f0f0f0;
            padding: 8px 16px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #4CAF50;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 6px;
            border: none;
            border-right: 1px solid #d9d9d9;
            border-bottom: 1px solid #d9d9d9;
        }
    """)

    window = GuitarTabsApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()