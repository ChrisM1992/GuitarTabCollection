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
        QMainWindow, QDialog {
            background-color: #2d2d30;
            color: #e0e0e0;
        }
        QTableView {
            QTableView {
            background-color: #202022;
            color: #e0e0e0;
            selection-background-color: #0078d7;
            selection-color: white;
            gridline-color: #3e3e42;
            alternate-background-color: #2a2a2d;  /* Explicitly set alternate row color */
}
        }
        QPushButton {
            background-color: #ff5722;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #ff7043;
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
    """)

    window = GuitarTabsApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()