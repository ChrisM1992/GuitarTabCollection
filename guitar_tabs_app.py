import os
from PyQt5.QtWidgets import (QMainWindow, QTableView, QVBoxLayout,
                             QHBoxLayout, QWidget, QPushButton, QComboBox,
                             QLabel, QLineEdit, QHeaderView, QTabWidget,
                             QMessageBox, QFileDialog, QDialog, QFrame,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QPoint, QRegExp
from PyQt5.QtGui import QFont, QIcon

from tabs_data_model import TabsDataModel
from database_manager import DatabaseManager
from add_tab_dialog import AddTabDialog
from batch_add_dialog import BatchAddDialog


class AdvancedFilterDialog(QDialog):
    """Dialog for advanced filtering"""

    def __init__(self, bands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Filter")
        self.setMinimumWidth(300)

        # Main layout
        layout = QFormLayout(self)

        # Band filter
        self.band_filter = QComboBox()
        self.band_filter.addItem("Any")
        self.band_filter.addItems(sorted(bands))
        layout.addRow("Band:", self.band_filter)

        # Album filter
        self.album_filter = QLineEdit()
        layout.addRow("Album:", self.album_filter)

        # Rating filter
        self.rating_filter = QComboBox()
        self.rating_filter.addItems(["Any", "1+", "2+", "3+", "4+", "5"])
        layout.addRow("Rating:", self.rating_filter)

        # Tuning filter
        self.tuning_filter = QLineEdit()
        layout.addRow("Tuning:", self.tuning_filter)

        # Genre filter
        self.genre_filter = QLineEdit()
        layout.addRow("Genre:", self.genre_filter)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Reset | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.accept)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset_filters)
        layout.addRow(buttons)

    def reset_filters(self):
        """Reset all filters to default values"""
        self.band_filter.setCurrentIndex(0)
        self.album_filter.clear()
        self.rating_filter.setCurrentIndex(0)
        self.tuning_filter.clear()
        self.genre_filter.clear()

    def get_filter_data(self):
        """Get the filter criteria"""
        return {
            "band": self.band_filter.currentText() if self.band_filter.currentIndex() > 0 else "",
            "album": self.album_filter.text().strip(),
            "rating": self.rating_filter.currentIndex(),
            "tuning": self.tuning_filter.text().strip(),
            "genre": self.genre_filter.text().strip()
        }


class CustomProxyModel(QSortFilterProxyModel):
    """Custom proxy model for advanced filtering"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_rating = 0
        self.band_filter = ""
        self.album_filter = ""
        self.tuning_filter = ""
        self.genre_filter = ""

    def set_rating_filter(self, min_rating):
        """Set minimum rating filter"""
        self.min_rating = min_rating
        self.invalidateFilter()

    def set_advanced_filters(self, filters):
        """Set advanced filters"""
        self.band_filter = filters.get("band", "")
        self.album_filter = filters.get("album", "")
        self.min_rating = filters.get("rating", 0)
        self.tuning_filter = filters.get("tuning", "")
        self.genre_filter = filters.get("genre", "")
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Custom filter implementation"""
        # First apply the standard filter (text-based)
        if not super().filterAcceptsRow(source_row, source_parent):
            return False

        source_model = self.sourceModel()

        # Apply rating filter
        if self.min_rating > 0:
            rating_idx = source_model.index(source_row, 5, source_parent)  # 5 is Rating column
            rating = int(source_model._data[source_row][5])
            min_value = self.min_rating
            if min_value == 5:  # Handle "5" case separately
                if rating < 5:
                    return False
            else:  # Handle "1+" through "4+"
                if rating < min_value:
                    return False

        # Apply band filter
        if self.band_filter:
            band_idx = source_model.index(source_row, 1, source_parent)  # 1 is Band column
            band = str(source_model._data[source_row][1])
            if not self.band_filter.lower() in band.lower():
                return False

        # Apply album filter
        if self.album_filter:
            album_idx = source_model.index(source_row, 2, source_parent)  # 2 is Album column
            album = str(source_model._data[source_row][2])
            if not self.album_filter.lower() in album.lower():
                return False

        # Apply tuning filter
        if self.tuning_filter:
            tuning_idx = source_model.index(source_row, 4, source_parent)  # 4 is Tuning column
            tuning = str(source_model._data[source_row][4])
            if not self.tuning_filter.lower() in tuning.lower():
                return False

        # Apply genre filter
        if self.genre_filter:
            genre_idx = source_model.index(source_row, 6, source_parent)  # 6 is Genre column
            genre = str(source_model._data[source_row][6])
            if not self.genre_filter.lower() in genre.lower():
                return False

        return True


class GuitarTabsApp(QMainWindow):
    """Main application window for the Guitar Tabs Collection Manager"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guitar Tabs Collection Manager")
        self.setMinimumSize(900, 600)

        # Variables for window dragging
        self.draggable = True
        self.dragging_threshold = 5
        self.drag_position = None

        # Set up database
        app_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(app_dir, "guitar_tabs.db")
        self.db_manager = DatabaseManager(db_path)

        # Initialize UI
        self.initUI()

        # Load data
        self.load_data()

    def show_add_dialog(self):
        """Show dialog to add a new tab"""
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

        # Batch add button
        self.batch_add_btn = QPushButton("Batch Add")
        self.batch_add_btn.clicked.connect(self.show_batch_add_dialog)
        top_controls.addWidget(self.batch_add_btn)

        # Delete tab button
        self.delete_btn = QPushButton("Delete Selected Tab")
        self.delete_btn.clicked.connect(self.delete_selected_tab)
        top_controls.addWidget(self.delete_btn)

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

        # Filter field dropdown
        self.filter_field = QComboBox()
        self.filter_field.addItems(["All Fields", "Band", "Album", "Title", "Tuning", "Genre"])
        filter_layout.addWidget(self.filter_field)

        # Text filter
        self.filter_text = QLineEdit()
        self.filter_text.setPlaceholderText("Type to filter...")
        self.filter_text.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_text)

        # Rating filter
        filter_layout.addWidget(QLabel("Rating:"))
        self.rating_filter = QComboBox()
        self.rating_filter.addItems(["Any", "1+", "2+", "3+", "4+", "5"])
        self.rating_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.rating_filter)

        # Advanced filter button
        self.adv_filter_btn = QPushButton("Advanced Filter")
        self.adv_filter_btn.clicked.connect(self.show_advanced_filter)
        filter_layout.addWidget(self.adv_filter_btn)

        main_layout.addLayout(filter_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

    def show_batch_add_dialog(self):
        """Show dialog to add multiple tabs at once"""
        # Get list of band names from the database
        bands = [band[1] for band in self.db_manager.get_all_bands()]

        # Create and show the batch add dialog
        dialog = BatchAddDialog(bands, self)

        # Execute the dialog and wait for user input
        if dialog.exec_() == QDialog.Accepted:
            try:
                # Get the entered data
                tabs_data = dialog.getTabsData()

                # Add the tabs to the database
                for tab in tabs_data:
                    self.db_manager.add_tab(tab)

                # Refresh the table view
                self.load_data()

                # Show success message
                self.statusBar().showMessage(f"Successfully added {len(tabs_data)} tabs")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add tabs: {str(e)}")

    def import_from_excel(self):
        """Import data from Excel file"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "",
                                                   "Excel Files (*.xlsx *.xls);;All Files (*)",
                                                   options=options)
        if file_name:
            try:
                # Confirm import
                if QMessageBox.question(self, "Confirm Import",
                                        "Importing will add new tabs from the Excel file. Continue?",
                                        QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                    # Import data
                    success = self.db_manager.import_from_excel(file_name)

                    if success:
                        # Reload data
                        self.load_data()

                        # Show success message
                        self.statusBar().showMessage(f"Imported data from {os.path.basename(file_name)}")
                    else:
                        QMessageBox.warning(self, "Warning",
                                            "Import completed with errors. Some data may not have been imported.")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import Excel file: {str(e)}")

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
                proxy_model = CustomProxyModel()
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
                    proxy_model = CustomProxyModel()
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

    def show_advanced_filter(self):
        """Show advanced filter dialog"""
        # Get list of band names
        bands = [band[1] for band in self.db_manager.get_all_bands()]

        # Create and show dialog
        dialog = AdvancedFilterDialog(bands, self)

        if dialog.exec_() == QDialog.Accepted:
            # Get filter criteria
            filters = dialog.get_filter_data()

            # Apply to current table view
            current_tab = self.tabs_widget.currentWidget()
            if isinstance(current_tab, QTableView):
                model = current_tab.model()
                if isinstance(model, CustomProxyModel):
                    model.set_advanced_filters(filters)
                    self.statusBar().showMessage("Advanced filter applied")

    def apply_filter(self):
        """Apply text and rating filter to the current table view"""
        if self.tabs_widget.count() == 0:
            return

        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return

        filter_text = self.filter_text.text()
        filter_field = self.filter_field.currentText()
        rating_index = self.rating_filter.currentIndex()

        proxy_model = current_tab.model()
        if not isinstance(proxy_model, CustomProxyModel):
            return

        # Map field names to column indices
        field_map = {
            "All Fields": -1,
            "Band": 1,
            "Album": 2,
            "Title": 3,
            "Tuning": 4,
            "Genre": 6
        }

        # Set filter column based on selection
        column_index = field_map.get(filter_field, -1)
        proxy_model.setFilterKeyColumn(column_index)

        # Set rating filter
        proxy_model.set_rating_filter(rating_index)

        # Apply text filter
        proxy_model.setFilterFixedString(filter_text)

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

    # Event handlers for dragging the window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.draggable:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()