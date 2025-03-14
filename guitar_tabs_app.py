import os
from PyQt5.QtWidgets import (QMainWindow, QTableView, QVBoxLayout,
                             QHBoxLayout, QWidget, QPushButton, QComboBox,
                             QLabel, QLineEdit, QHeaderView, QTabWidget,
                             QMessageBox, QFileDialog, QDialog, QFrame,
                             QFormLayout, QDialogButtonBox, QMenu, QAction)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QPoint, QRegExp
from PyQt5.QtGui import QFont, QIcon

from tabs_data_model import TabsDataModel
from database_manager import DatabaseManager
from add_tab_dialog import AddTabDialog
from batch_add_dialog import BatchAddDialog
from PyQt5.QtWidgets import (QSizePolicy)
from PyQt5.QtCore import Qt


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
        
        # Track current view mode
        self.current_view = "all"  # 'all' or 'learned'

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
        top_controls.setAlignment(Qt.AlignLeft)  # Align buttons to the left

        # Mode selection buttons
        self.mode_buttons_layout = QHBoxLayout()
        
        # All Tabs button
        self.all_tabs_btn = QPushButton("All Tabs")
        self.all_tabs_btn.setCheckable(True)
        self.all_tabs_btn.setChecked(True)
        self.all_tabs_btn.clicked.connect(lambda: self.switch_mode("all"))
        self.mode_buttons_layout.addWidget(self.all_tabs_btn)
        
        # Learned Tabs button
        self.learned_tabs_btn = QPushButton("Learned")
        self.learned_tabs_btn.setCheckable(True)
        self.learned_tabs_btn.clicked.connect(lambda: self.switch_mode("learned"))
        self.mode_buttons_layout.addWidget(self.learned_tabs_btn)
        
        # Style the mode buttons
        self.all_tabs_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #0078d7;
                border: none;
            }
        """)
        self.learned_tabs_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #4CAF50;
                border: none;
            }
        """)
        
        top_controls.addLayout(self.mode_buttons_layout)
        
        # Add some spacing
        top_controls.addSpacing(20)
        
        # Add new tab button
        self.add_btn = QPushButton("Add New Tab")
        self.add_btn.clicked.connect(self.show_add_dialog)
        top_controls.addWidget(self.add_btn)

        # Batch add button
        self.batch_add_btn = QPushButton("Add multiple")
        self.batch_add_btn.clicked.connect(self.show_batch_add_dialog)
        top_controls.addWidget(self.batch_add_btn)

        # Delete tab button
        self.delete_btn = QPushButton("Delete Selected Tab(s)")
        self.delete_btn.clicked.connect(self.delete_selected_tabs)
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

        # Button sizes
        self.add_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_btn.adjustSize()

        self.batch_add_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.batch_add_btn.adjustSize()

        self.delete_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.delete_btn.adjustSize()

    def switch_mode(self, mode):
        """Switch between All Tabs and Learned Tabs views"""
        if mode == self.current_view:
            return
            
        self.current_view = mode
        
        # Update button states
        if mode == "all":
            self.all_tabs_btn.setChecked(True)
            self.learned_tabs_btn.setChecked(False)
        else:  # mode == "learned"
            self.all_tabs_btn.setChecked(False)
            self.learned_tabs_btn.setChecked(True)
        
        # Reload data with new mode
        self.load_data()

    def show_context_menu(self, position):
        """Show context menu for tabs table"""
        # Get current table view
        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return
        
        # Get selected index
        index = current_tab.indexAt(position)
        if not index.isValid():
            return
        
        # Create menu
        menu = QMenu()
        
        # Add actions
        add_to_learned_action = menu.addAction("Mark as Learned")
        delete_action = menu.addAction("Delete Tab")
        
        # Show menu
        action = menu.exec_(current_tab.viewport().mapToGlobal(position))
        
        if action == add_to_learned_action:
            self.add_tab_to_learned(current_tab, index)
        elif action == delete_action:
            self.delete_selected_tabs()
    
    def show_learned_context_menu(self, position):
        """Show context menu for learned tabs table"""
        # Get current table view
        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return
        
        # Get selected index
        index = current_tab.indexAt(position)
        if not index.isValid():
            return
        
        # Create menu
        menu = QMenu()
        
        # Add action
        remove_action = menu.addAction("Remove from Learned")
        
        # Show menu
        action = menu.exec_(current_tab.viewport().mapToGlobal(position))
        
        if action == remove_action:
            self.remove_from_learned(current_tab, index)
    
    def add_tab_to_learned(self, table_view, index):
        """Add a tab to the learned tabs table"""
        # Get proxy model and source model
        proxy_model = table_view.model()
        source_model = proxy_model.sourceModel()
        
        # Map proxy index to source index
        source_row = proxy_model.mapToSource(index).row()
        
        # Get tab ID from first column
        tab_id = source_model._data[source_row][0]
        tab_title = source_model._data[source_row][3]  # Title column
        
        try:
            # Add to learned tabs
            success = self.db_manager.add_to_learned(tab_id)
            
            if success:
                # Show success message
                self.statusBar().showMessage(f"'{tab_title}' marked as learned")
                
                # If we're in the learned view, reload to show the new tab
                if self.current_view == "learned":
                    self.load_data()
            else:
                self.statusBar().showMessage(f"'{tab_title}' already marked as learned")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to mark tab as learned: {str(e)}")
    
    def remove_from_learned(self, table_view, index):
        """Remove a tab from the learned tabs table"""
        # Get proxy model and source model
        proxy_model = table_view.model()
        source_model = proxy_model.sourceModel()
        
        # Map proxy index to source index
        source_row = proxy_model.mapToSource(index).row()
        
        # Get tab ID from first column
        tab_id = source_model._data[source_row][0]
        tab_title = source_model._data[source_row][3]  # Title column
        
        try:
            # Remove from learned tabs
            self.db_manager.remove_from_learned(tab_id)
            
            # Reload data
            self.load_data()
            
            # Show success message
            self.statusBar().showMessage(f"'{tab_title}' removed from learned tabs")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove tab from learned: {str(e)}")

    def load_data(self):
        """Load data from the database"""
        try:
            # Clear existing tabs
            self.tabs_widget.clear()
            
            # Get all bands
            bands = self.db_manager.get_all_bands()
            
            if self.current_view == "all":
                # Standard columns for all tabs view
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
                    all_tabs_table.setSelectionMode(QTableView.ExtendedSelection)
                    
                    # Enable context menu
                    all_tabs_table.setContextMenuPolicy(Qt.CustomContextMenu)
                    all_tabs_table.customContextMenuRequested.connect(self.show_context_menu)
                    
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
                        band_table.setSelectionMode(QTableView.ExtendedSelection)
                        
                        # Enable context menu
                        band_table.setContextMenuPolicy(Qt.CustomContextMenu)
                        band_table.customContextMenuRequested.connect(self.show_context_menu)

                        # Add to tabs widget
                        self.tabs_widget.addTab(band_table, band_name)
            
            else:  # self.current_view == "learned"
                # Columns for learned tabs view
                columns = ["ID", "Band", "Album", "Title", "Tuning", "Rating", "Genre", "Learned Date"]
                
                # Get learned tabs
                learned_tabs = self.db_manager.get_all_learned_tabs()
                
                if learned_tabs:
                    # Create "All Learned" tab
                    learned_table = QTableView()
                    learned_model = TabsDataModel(learned_tabs, columns)
                    proxy_model = CustomProxyModel()
                    proxy_model.setSourceModel(learned_model)
                    proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
                    learned_table.setModel(proxy_model)
                    
                    # Configure table appearance
                    learned_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                    learned_table.hideColumn(0)  # Hide ID column
                    learned_table.setSortingEnabled(True)
                    learned_table.setAlternatingRowColors(True)
                    learned_table.setSelectionBehavior(QTableView.SelectRows)
                    learned_table.setSelectionMode(QTableView.ExtendedSelection)
                    
                    # Enable context menu for removing from learned
                    learned_table.setContextMenuPolicy(Qt.CustomContextMenu)
                    learned_table.customContextMenuRequested.connect(self.show_learned_context_menu)
                    
                    # Add to tabs widget
                    self.tabs_widget.addTab(learned_table, "All Learned")
                    
                    # Create tabs for bands with learned songs
                    band_learned_tabs = {}
                    for tab in learned_tabs:
                        band_name = tab[1]  # Band column
                        if band_name not in band_learned_tabs:
                            band_learned_tabs[band_name] = []
                        band_learned_tabs[band_name].append(tab)
                    
                    # Create a tab for each band with learned songs
                    for band_name, tabs in band_learned_tabs.items():
                        band_table = QTableView()
                        band_model = TabsDataModel(tabs, columns)
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
                        band_table.setSelectionMode(QTableView.ExtendedSelection)
                        
                        # Enable context menu
                        band_table.setContextMenuPolicy(Qt.CustomContextMenu)
                        band_table.customContextMenuRequested.connect(self.show_learned_context_menu)
                        
                        # Add to tabs widget
                        self.tabs_widget.addTab(band_table, band_name)
                else:
                    # Create an empty tab if no learned tabs
                    empty_widget = QWidget()
                    empty_layout = QVBoxLayout(empty_widget)
                    empty_label = QLabel("No learned tabs yet. Right-click on tabs in 'All Tabs' view to mark them as learned.")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_layout.addWidget(empty_label)
                    self.tabs_widget.addTab(empty_widget, "Learned")
            
            # Update status bar
            if self.current_view == "all":
                self.statusBar().showMessage(f"Loaded {len(bands)} bands")
            else:
                learned_count = len(self.db_manager.get_all_learned_tabs())
                self.statusBar().showMessage(f"Loaded {learned_count} learned tabs")

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

    def show_add_dialog(self):
        """Show dialog to add a new tab"""
        # Get list of band names
        bands = [band[1] for band in self.db_manager.get_all_bands()]

        # Get tunings from database
        tunings = self.db_manager.get_all_tunings()

        # Show dialog
        dialog = AddTabDialog(bands, self)

        # Set the tunings from database if method available
        if hasattr(dialog, 'tunings') and hasattr(dialog.tuning, 'clear'):
            dialog.tunings = tunings
            dialog.tuning.clear()
            dialog.tuning.addItems(tunings)

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

    def show_batch_add_dialog(self):
        """Show dialog to add multiple tabs at once"""
        # Get list of band names from the database
        bands = [band[1] for band in self.db_manager.get_all_bands()]

        # Get tunings from database
        tunings = self.db_manager.get_all_tunings()

        # Create and show the batch add dialog
        dialog = BatchAddDialog(bands, self)

        # Set the tunings from database if method available
        if hasattr(dialog, 'tunings') and hasattr(dialog.tuning, 'clear'):
            dialog.tunings = tunings
            dialog.tuning.clear()
            dialog.tuning.addItems(tunings)

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

    def delete_selected_tabs(self):
        """Delete the selected tabs"""
        # Get current tab widget
        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return

        # Get selected rows
        selection_model = current_tab.selectionModel()
        if not selection_model.hasSelection():
            QMessageBox.warning(self, "Warning", "No tabs selected.")
            return

        # Get all selected row indices
        selected_rows = set()
        for index in selection_model.selectedIndexes():
            selected_rows.add(index.row())

        # Confirm deletion
        if QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete {len(selected_rows)} selected tab(s)?",
                QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            try:
                # Get proxy model and source model
                proxy_model = current_tab.model()
                source_model = proxy_model.sourceModel()

                # Collect all tab IDs to delete (from last to first to avoid index shifting)
                tab_ids = []
                for proxy_row in sorted(list(selected_rows), reverse=True):
                    # Map proxy index to source index
                    source_row = proxy_model.mapToSource(proxy_model.index(proxy_row, 0)).row()
                    # Get tab ID from first column
                    tab_id = source_model._data[source_row][0]
                    tab_ids.append(tab_id)

                # Delete all tabs from database
                for tab_id in tab_ids:
                    self.db_manager.delete_tab(tab_id)

                # Reload data
                self.load_data()

                # Show success message
                self.statusBar().showMessage(f"{len(tab_ids)} tabs deleted successfully")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete tabs: {str(e)}")

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