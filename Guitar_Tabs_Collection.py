import sys
import os
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableView, QVBoxLayout,
                            QHBoxLayout, QWidget, QPushButton, QComboBox,
                            QLabel, QLineEdit, QHeaderView, QTabWidget,
                            QMessageBox, QFileDialog, QDialog, QFormLayout,
                            QSpinBox, QDialogButtonBox)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex

class TabsDataModel(QAbstractTableModel):
    """Data model for representing the guitar tabs collection"""

    def __init__(self, data=None, columns=None):
        super().__init__()
        self._data = data if data is not None else []
        self.columns = columns if columns is not None else []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            # Return the value from the data list
            value = self._data[index.row()][index.column()]
            # Handle different data types appropriately
            if isinstance(value, (float, int)):
                return str(value)
            return str(value)

        if role == Qt.BackgroundRole:
            # Color rows alternately for better readability
            if index.row() % 2 == 0:
                return QColor(240, 240, 240)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            row = index.row()
            column = index.column()

            # Create a new row list with the updated value
            new_row = list(self._data[row])
            new_row[column] = value

            # Replace the old row with the new one
            self._data[row] = tuple(new_row)

            # Emit the dataChanged signal
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        # Make cells editable
        return super().flags(index) | Qt.ItemIsEditable

    def addRow(self, row_data):
        # Add new row to the model
        self.beginInsertRows(Qt.QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(tuple(row_data))
        self.endInsertRows()
        return True

    def removeRow(self, row, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        del self._data[row]
        self.endRemoveRows()
        return True

    def getAllData(self):
        # Return all data
        return self._data


class AddTabDialog(QDialog):
    """Dialog for adding a new tab entry"""

    def __init__(self, bands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Tab")
        self.resize(400, 300)

        layout = QFormLayout(self)

        # Band selection (existing bands or new one)
        self.band_combo = QComboBox()
        self.band_combo.addItems(["-- New Band --"] + sorted(bands))
        self.band_combo.currentTextChanged.connect(self.onBandChanged)
        layout.addRow("Band:", self.band_combo)

        # New band name (only visible when "-- New Band --" is selected)
        self.new_band = QLineEdit()
        self.new_band.setPlaceholderText("Enter new band name")
        self.new_band_label = QLabel("New Band Name:")
        layout.addRow(self.new_band_label, self.new_band)

        # Other fields
        self.album = QLineEdit()
        self.title = QLineEdit()
        self.tuning = QLineEdit()
        self.tuning.setPlaceholderText("e.g., Standard, Drop D, etc.")
        self.rating = QSpinBox()
        self.rating.setMinimum(1)
        self.rating.setMaximum(5)
        self.genre = QLineEdit()

        layout.addRow("Album:", self.album)
        layout.addRow("Title:", self.title)
        layout.addRow("Tuning:", self.tuning)
        layout.addRow("Rating (1-5):", self.rating)
        layout.addRow("Genre:", self.genre)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        # Initial state
        self.onBandChanged(self.band_combo.currentText())

    def onBandChanged(self, text):
        # Show/hide new band name field
        show_new_band = (text == "-- New Band --")
        self.new_band_label.setVisible(show_new_band)
        self.new_band.setVisible(show_new_band)

    def getTabData(self):
        """Get the entered tab data"""
        band = self.band_combo.currentText()

        # If "-- New Band --" is selected, get the name from the new band field
        if band == "-- New Band --":
            band = self.new_band.text().strip()
            if not band:
                return None  # No band name entered

        # Return the tab data
        return {
            "band": band,
            "album": self.album.text().strip(),
            "title": self.title.text().strip(),
            "tuning": self.tuning.text().strip(),
            "rating": self.rating.value(),
            "genre": self.genre.text().strip()
        }


class DatabaseManager:
    """Manager for SQLite database operations"""

    def __init__(self, db_path):
        """Initialize the database manager"""
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create bands table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bands (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        ''')

        # Create tabs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tabs (
            id INTEGER PRIMARY KEY,
            band_id INTEGER NOT NULL,
            album TEXT,
            title TEXT NOT NULL,
            tuning TEXT,
            rating INTEGER,
            genre TEXT,
            FOREIGN KEY (band_id) REFERENCES bands (id)
        )
        ''')

        conn.commit()
        conn.close()

    def get_all_bands(self):
        """Get all bands from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM bands ORDER BY name")
        bands = cursor.fetchall()

        conn.close()
        return bands

    def get_band_id(self, band_name):
        """Get band ID by name, create if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try to get existing band
        cursor.execute("SELECT id FROM bands WHERE name = ?", (band_name,))
        result = cursor.fetchone()

        if result:
            band_id = result[0]
        else:
            # Create new band
            cursor.execute("INSERT INTO bands (name) VALUES (?)", (band_name,))
            band_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return band_id

    def get_tabs_for_band(self, band_id):
        """Get all tabs for a specific band"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre
        FROM tabs t
        JOIN bands b ON t.band_id = b.id
        WHERE t.band_id = ?
        ORDER BY t.album, t.title
        ''', (band_id,))

        tabs = cursor.fetchall()

        conn.close()
        return tabs

    def get_all_tabs(self):
        """Get all tabs from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre
        FROM tabs t
        JOIN bands b ON t.band_id = b.id
        ORDER BY b.name, t.album, t.title
        ''')

        tabs = cursor.fetchall()

        conn.close()
        return tabs

    def add_tab(self, tab_data):
        """Add a new tab to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get or create band
            band_id = self.get_band_id(tab_data["band"])

            # Insert tab
            cursor.execute('''
            INSERT INTO tabs (band_id, album, title, tuning, rating, genre)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                band_id,
                tab_data["album"],
                tab_data["title"],
                tab_data["tuning"],
                tab_data["rating"],
                tab_data["genre"]
            ))

            conn.commit()
            tab_id = cursor.lastrowid

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return tab_id

    def update_tab(self, tab_id, tab_data):
        """Update an existing tab"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get or create band
            band_id = self.get_band_id(tab_data["band"])

            # Update tab
            cursor.execute('''
            UPDATE tabs
            SET band_id = ?, album = ?, title = ?, tuning = ?, rating = ?, genre = ?
            WHERE id = ?
            ''', (
                band_id,
                tab_data["album"],
                tab_data["title"],
                tab_data["tuning"],
                tab_data["rating"],
                tab_data["genre"],
                tab_id
            ))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_tab(self, tab_id):
        """Delete a tab from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM tabs WHERE id = ?", (tab_id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def import_from_excel(self, excel_path):
        """Import data from Excel file"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(excel_path)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Process each sheet (band)
            for sheet_name in excel_file.sheet_names:
                # Read sheet
                df = excel_file.parse(sheet_name)

                # Create or get band
                cursor.execute("SELECT id FROM bands WHERE name = ?", (sheet_name,))
                result = cursor.fetchone()

                if result:
                    band_id = result[0]
                else:
                    cursor.execute("INSERT INTO bands (name) VALUES (?)", (sheet_name,))
                    band_id = cursor.lastrowid

                # Process each row
                for _, row in df.iterrows():
                    # Extract data from row
                    try:
                        album = row.get('Album Name', '')
                        title = row.get('Title', '')
                        tuning = row.get('Tuning', '')
                        rating = row.get('Rating', 0)
                        genre = row.get('Genre', '')

                        # Insert tab
                        cursor.execute('''
                        INSERT INTO tabs (band_id, album, title, tuning, rating, genre)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (band_id, album, title, tuning, rating, genre))
                    except Exception as e:
                        print(f"Error importing row: {e}")
                        continue

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            print(f"Error importing Excel file: {e}")
            return False


class GuitarTabsApp(QMainWindow):
    """Main application window for the Guitar Tabs Collection Manager"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guitar Tabs Collection Manager")
        self.setMinimumSize(900, 600)

        # Set up database
        app_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(app_dir, "guitar_tabs.db")
        self.db_manager = DatabaseManager(db_path)

        # Initialize UI
        self.initUI()

        # Load data
        self.load_data()

    def initUI(self):
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top controls
        top_controls = QHBoxLayout()

        # Add new tab button
        self.add_btn = QPushButton("Add New Tab")
        self.add_btn.clicked.connect(self.show_add_dialog)
        top_controls.addWidget(self.add_btn)

        # Delete tab button
        self.delete_btn = QPushButton("Delete Selected Tab")
        self.delete_btn.clicked.connect(self.delete_selected_tab)
        top_controls.addWidget(self.delete_btn)

        # Import button
        self.import_btn = QPushButton("Import from Excel (Does not work) ")
        self.import_btn.clicked.connect(self.import_from_excel)
        top_controls.addWidget(self.import_btn)
        top_controls.addStretch()

        main_layout.addLayout(top_controls)

        # Tabs widget to show different bands
        self.tabs_widget = QTabWidget()
        self.tabs_widget.setTabPosition(QTabWidget.North)
        self.tabs_widget.setMovable(True)
        self.tabs_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs_widget)

        # Filter controls
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Filter:"))

        self.filter_field = QComboBox()
        self.filter_field.addItems(["All Fields", "Band", "Album", "Title", "Tuning", "Genre"])
        filter_layout.addWidget(self.filter_field)

        self.filter_text = QLineEdit()
        self.filter_text.setPlaceholderText("Type to filter...")
        self.filter_text.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_text)

        main_layout.addLayout(filter_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

    def load_data(self):
        """Load data from the database"""
        try:
            # Clear existing tabs
            self.tabs_widget.clear()

            # Get all bands
            bands = self.db_manager.get_all_bands()

            # Create a tab for each band
            columns = ["ID", "Band", "Album", "Title", "Tuning", "Rating", "Genre"]

            # Create "All Tabs" tab
            all_tabs = self.db_manager.get_all_tabs()
            if all_tabs:
                all_tabs_table = QTableView()
                all_tabs_model = TabsDataModel(all_tabs, columns)
                proxy_model = QSortFilterProxyModel()
                proxy_model.setSourceModel(all_tabs_model)
                proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
                all_tabs_table.setModel(proxy_model)

                # Configure table appearance
                all_tabs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                all_tabs_table.hideColumn(0)  # Hide ID column
                all_tabs_table.setSortingEnabled(True)
                all_tabs_table.setAlternatingRowColors(True)
                all_tabs_table.setSelectionBehavior(QTableView.SelectRows)

                # Add to tabs widget
                self.tabs_widget.addTab(all_tabs_table, "All Tabs")

            # Create a tab for each band
            for band_id, band_name in bands:
                # Get tabs for this band
                band_tabs = self.db_manager.get_tabs_for_band(band_id)

                if band_tabs:
                    band_table = QTableView()
                    band_model = TabsDataModel(band_tabs, columns)
                    proxy_model = QSortFilterProxyModel()
                    proxy_model.setSourceModel(band_model)
                    proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
                    band_table.setModel(proxy_model)

                    # Configure table appearance
                    band_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                    band_table.hideColumn(0)  # Hide ID column
                    band_table.setSortingEnabled(True)
                    band_table.setAlternatingRowColors(True)
                    band_table.setSelectionBehavior(QTableView.SelectRows)

                    # Add to tabs widget
                    self.tabs_widget.addTab(band_table, band_name)

            self.statusBar().showMessage(f"Loaded {len(bands)} bands")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
            self.statusBar().showMessage("Error loading data")

    def on_tab_changed(self, index):
        """Handler for when user switches tabs"""
        # Update status bar
        if index >= 0:
            tab_name = self.tabs_widget.tabText(index)
            count = 0
            if isinstance(self.tabs_widget.widget(index), QTableView):
                model = self.tabs_widget.widget(index).model()
                if isinstance(model, QSortFilterProxyModel):
                    count = model.rowCount()
            self.statusBar().showMessage(f"{tab_name}: {count} tabs")

    def apply_filter(self):
        """Apply filter to the current table view"""
        if self.tabs_widget.count() == 0:
            return

        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return

        filter_text = self.filter_text.text()
        filter_field = self.filter_field.currentText()

        proxy_model = current_tab.model()
        if not isinstance(proxy_model, QSortFilterProxyModel):
            return

        # Map field names to column indices
        field_map = {
            "All Fields": -1,
            "Band": 1,
            "Album": 2,
            "Title": 3,
            "Tuning": 4,
            "Rating": 5,
            "Genre": 6
        }

        # Set filter column based on selection
        column_index = field_map.get(filter_field, -1)
        proxy_model.setFilterKeyColumn(column_index)

        # Apply filter
        proxy_model.setFilterFixedString(filter_text)

    def show_add_dialog(self):
        """Show dialog to add a new tab entry"""
        # Get list of band names
        bands = [band[1] for band in self.db_manager.get_all_bands()]

        # Show dialog
        dialog = AddTabDialog(bands, self)
        if dialog.exec_() == QDialog.Accepted:
            # Get data from dialog
            tab_data = dialog.getTabData()
            if tab_data:
                try:
                    # Add to database
                    self.db_manager.add_tab(tab_data)

                    # Reload data
                    self.load_data()

                    # Show success message
                    self.statusBar().showMessage(f"Added new tab: {tab_data['title']} by {tab_data['band']}")

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tab: {str(e)}")

    def delete_selected_tab(self):
        """Delete the selected tab"""
        # Get current tab widget
        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return

        # Get selected row
        selected_indexes = current_tab.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Warning", "No tab selected.")
            return

        # Get row and ID
        proxy_model = current_tab.model()
        source_model = proxy_model.sourceModel()
        proxy_row = selected_indexes[0].row()
        source_row = proxy_model.mapToSource(proxy_model.index(proxy_row, 0)).row()
        tab_id = source_model._data[source_row][0]

        # Confirm deletion
        if QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this tab?",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                # Delete from database
                self.db_manager.delete_tab(tab_id)

                # Reload data
                self.load_data()

                # Show success message
                self.statusBar().showMessage("Tab deleted successfully")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete tab: {str(e)}")

    

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
