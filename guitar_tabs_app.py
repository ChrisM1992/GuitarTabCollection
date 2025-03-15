import os
import csv
from PyQt5.QtWidgets import (QMainWindow, QTableView, QVBoxLayout,
                             QHBoxLayout, QWidget, QPushButton, QComboBox,
                             QLabel, QLineEdit, QHeaderView, QTabWidget,
                             QMessageBox, QFileDialog, QDialog, QFrame,
                             QFormLayout, QDialogButtonBox, QMenu, QAction)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QPoint, QRegExp, QItemSelectionModel
from PyQt5.QtGui import QFont, QIcon

from tabs_data_model import TabsDataModel
from database_manager import DatabaseManager
from add_tab_dialog import AddTabDialog
from add_tab_multi import BatchAddDialog
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
        self.setMinimumSize(1400, 800)

        # Variables for window dragging
        self.draggable = True
        self.dragging_threshold = 5
        self.drag_position = None

        # Set up database
        app_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(app_dir, "guitar_tabs.db")
        self.db_manager = DatabaseManager(db_path)
        
        # Clean up empty bands on startup - with error handling
        try:
            self.db_manager.clean_up_empty_bands()
        except Exception as e:
            print(f"Warning: Could not clean up empty bands on startup: {str(e)}")
        
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
        
        # Mode selection buttons (keep on the left)
        self.mode_buttons_layout = QHBoxLayout()
        
        # Tabs Collection button
        self.all_tabs_btn = QPushButton("Tabs Collection")
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
                background-color: #c19757;          
                border: none;
            }
        """)
        self.learned_tabs_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #c19757;
                border: none;
            }
        """)
        
        # Add the mode buttons to the left side
        top_controls.addLayout(self.mode_buttons_layout)
        
        # Add a stretching space to push the next buttons to the right
        top_controls.addStretch(1)
        
        # Action buttons (on the right)
        action_buttons_layout = QHBoxLayout()
        
        # Add new tab button
        self.add_btn = QPushButton("Add New Tab")
        self.add_btn.clicked.connect(self.show_add_dialog)
        action_buttons_layout.addWidget(self.add_btn)

        # Add multiple button
        self.batch_add_btn = QPushButton("Add multiple")
        self.batch_add_btn.clicked.connect(self.show_batch_add_dialog)
        action_buttons_layout.addWidget(self.batch_add_btn)

        # CSV Import button
        self.csv_import_btn = QPushButton("Import CSV")
        self.csv_import_btn.clicked.connect(self.import_from_csv)
        action_buttons_layout.addWidget(self.csv_import_btn)

        # Apply same size policy as other buttons
        self.csv_import_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.csv_import_btn.adjustSize()
        
        # Add the action buttons to the right side
        top_controls.addLayout(action_buttons_layout)

        # Add the top controls to the main layout
        main_layout.addLayout(top_controls)
        
        # Add spacing between buttons and table (increase this value for bigger gap)
        main_layout.addSpacing(20)

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
        try:
            # Get current table view
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return
            
            # Get index at position
            index = current_tab.indexAt(position)
            
            # Get selection model
            selection_model = current_tab.selectionModel()
            
            # If no selection and clicked on a valid item, select that item
            if not selection_model.hasSelection() and index.isValid():
                selection_model.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
            
            # Get selected count
            selected_rows = selection_model.selectedRows()
            selected_count = len(selected_rows)
            
            if selected_count == 0:
                return  # No selection, don't show menu
            
            # Create menu
            menu = QMenu()
            
            # Add actions based on current view
            if self.current_view == "all":
                mark_action_text = f"Mark {selected_count} as Learned" if selected_count > 1 else "Mark as Learned"
                add_to_learned_action = menu.addAction(mark_action_text)
            else:  # "learned" view
                remove_action_text = f"Remove {selected_count} from Learned" if selected_count > 1 else "Remove from Learned"
                remove_from_learned_action = menu.addAction(remove_action_text)
            
            # Always add delete action
            delete_action_text = f"Delete {selected_count} Tab(s)" if selected_count > 1 else "Delete Tab"
            delete_action = menu.addAction(delete_action_text)
            
            # Show menu
            action = menu.exec_(current_tab.viewport().mapToGlobal(position))
            
            # Process action
            if action is None:
                return
                
            if self.current_view == "all" and action == add_to_learned_action:
                self.add_tab_to_learned(current_tab)
            elif self.current_view == "learned" and action == remove_from_learned_action:
                self.remove_from_learned(current_tab)
            elif action == delete_action:
                self.delete_selected_tabs()
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error in context menu: {str(e)}")
            self.statusBar().showMessage(f"Error in context menu: {str(e)}")
    
    def show_learned_context_menu(self, position):
        """Show context menu for learned tabs table"""
        # Get current table view
        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return
        
        # Get selection model
        selection_model = current_tab.selectionModel()
        
        # Check if we have a selection
        if not selection_model.hasSelection():
            # If no selection, check if the clicked position is on a valid item
            index = current_tab.indexAt(position)
            if not index.isValid():
                return
                
            # If no selection but clicked on a valid item, select that item
            selection_model.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        
        # Get selected count
        selected_count = len(selection_model.selectedRows())
        
        # Create menu
        menu = QMenu()
        
        # Add action (with count in the text)
        remove_action_text = f"Remove {selected_count} from Learned" if selected_count > 1 else "Remove from Learned"
        remove_action = menu.addAction(remove_action_text)
        
        # Show menu
        action = menu.exec_(current_tab.viewport().mapToGlobal(position))
        
        if action == remove_action:
            # Don't pass index, let the method use the selection model
            self.remove_from_learned(current_tab)
    
    def add_tab_to_learned(self, table_view, index=None):
        """Add tab(s) to the learned tabs table"""
        # Get all selected rows
        selection_model = table_view.selectionModel()
        indices = selection_model.selectedRows()
        
        if not indices:
            # If no selected rows and a specific index was provided
            if index and index.isValid():
                indices = [index]
            else:
                return
        
        added_count = 0
        already_learned = 0
        tab_title = ""  # Initialize variable for status message
        
        # Process each selected row
        for idx in indices:
            proxy_model = table_view.model()
            source_model = proxy_model.sourceModel()
            source_row = proxy_model.mapToSource(idx).row()
            
            # Safely store title for single selection status message
            if len(indices) == 1:
                tab_title = source_model._data[source_row][3]  # Title column
            
            tab_id = source_model._data[source_row][0]
            
            try:
                # Add to learned tabs
                success = self.db_manager.add_to_learned(tab_id)
                if success:
                    added_count += 1
                else:
                    already_learned += 1
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to mark tab as learned: {str(e)}")
        
        # Status message - safely using tab_title only for single selections
        if len(indices) == 1:
            if added_count == 1:
                self.statusBar().showMessage(f"'{tab_title}' marked as learned")
            else:
                self.statusBar().showMessage(f"'{tab_title}' already marked as learned")
        else:
            self.statusBar().showMessage(f"{added_count} tabs marked as learned, {already_learned} already learned")
        
        # Reload if in Learned view
        if self.current_view == "learned":
            self.load_data()

    def remove_from_learned(self, table_view, index=None):
        """Remove tab(s) from the learned tabs table"""
        # Handle single or multiple selection
        if index and index.isValid():
            indices = [index]
        else:
            indices = table_view.selectionModel().selectedRows()
        
        if not indices:
            return
            
        removed_count = 0
        proxy_model = table_view.model()
        source_model = proxy_model.sourceModel()
        
        for idx in indices:
            source_row = proxy_model.mapToSource(idx).row()
            tab_id = source_model._data[source_row][0]
            
            try:
                self.db_manager.remove_from_learned(tab_id)
                removed_count += 1
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove tab from learned: {str(e)}")
        
        # Reload data
        self.load_data()
        
        # Show success message
        if len(indices) == 1:
            tab_title = source_model._data[source_row][3]  # Title column
            self.statusBar().showMessage(f"'{tab_title}' removed from learned tabs")
        else:
            self.statusBar().showMessage(f"{removed_count} tabs removed from learned tabs")

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
                
                # Create "General" tab for bands with less than 5 songs
                general_tabs = []
                bands_with_few_songs = set()
                
                # Create a tab for each band with 5 or more songs, collect others for General tab
                for band_id, band_name in bands:
                    # Get tabs for this band
                    band_tabs = self.db_manager.get_tabs_for_band(band_id)

                    if len(band_tabs) < 5:
                        # Add to general tabs
                        general_tabs.extend(band_tabs)
                        bands_with_few_songs.add(band_name)
                    elif band_tabs:
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
                
                # Add the General tab if there are any bands with less than 5 songs
                if general_tabs:
                    general_table = QTableView()
                    general_model = TabsDataModel(general_tabs, columns)
                    proxy_model = CustomProxyModel()
                    proxy_model.setSourceModel(general_model)
                    proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
                    general_table.setModel(proxy_model)

                    # Configure table appearance
                    general_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                    general_table.hideColumn(0)  # Hide ID column
                    general_table.setSortingEnabled(True)
                    general_table.setAlternatingRowColors(True)
                    general_table.setSelectionBehavior(QTableView.SelectRows)
                    general_table.setSelectionMode(QTableView.ExtendedSelection)
                    
                    # Enable context menu
                    general_table.setContextMenuPolicy(Qt.CustomContextMenu)
                    general_table.customContextMenuRequested.connect(self.show_context_menu)

                    # Add to tabs widget - place it right after "All Tabs"
                    self.tabs_widget.insertTab(1, general_table, "General")
                    
                    # Update status to show which bands are in General tab
                    bands_list = ", ".join(sorted(bands_with_few_songs))
                    general_table.setToolTip(f"Bands with fewer than 5 songs: {bands_list}")
            
            else:  # self.current_view == "learned"
                # Implementation for learned tabs remains the same
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
                    
                    # Create General tab for learned songs from bands with fewer than 5 learned songs
                    general_learned_tabs = []
                    bands_with_few_learned = set()
                    
                    # Group learned tabs by band
                    band_learned_tabs = {}
                    for tab in learned_tabs:
                        band_name = tab[1]  # Band column
                        if band_name not in band_learned_tabs:
                            band_learned_tabs[band_name] = []
                        band_learned_tabs[band_name].append(tab)
                    
                    # Create tabs for bands with 5+ learned songs, collect others for General
                    for band_name, tabs in band_learned_tabs.items():
                        if len(tabs) < 5:
                            # Add to general learned tabs
                            general_learned_tabs.extend(tabs)
                            bands_with_few_learned.add(band_name)
                        else:
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
                    
                    # Add General tab for learned if needed
                    if general_learned_tabs:
                        general_table = QTableView()
                        general_model = TabsDataModel(general_learned_tabs, columns)
                        proxy_model = CustomProxyModel()
                        proxy_model.setSourceModel(general_model)
                        proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
                        general_table.setModel(proxy_model)
                        
                        # Configure table appearance
                        general_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                        general_table.hideColumn(0)  # Hide ID column
                        general_table.setSortingEnabled(True)
                        general_table.setAlternatingRowColors(True)
                        general_table.setSelectionBehavior(QTableView.SelectRows)
                        general_table.setSelectionMode(QTableView.ExtendedSelection)
                        
                        # Enable context menu
                        general_table.setContextMenuPolicy(Qt.CustomContextMenu)
                        general_table.customContextMenuRequested.connect(self.show_learned_context_menu)
                        
                        # Add to tabs widget - place it right after "All Learned"
                        self.tabs_widget.insertTab(1, general_table, "General")
                        
                        # Update tooltip to show which bands are in General tab
                        bands_list = ", ".join(sorted(bands_with_few_learned))
                        general_table.setToolTip(f"Bands with fewer than 5 learned songs: {bands_list}")
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
        """Show dialog to add a new tab with duplicate checking"""
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
                    # Check if the tab already exists
                    if self.db_manager.tab_exists(tab_data["band"], tab_data["album"], tab_data["title"]):
                        QMessageBox.warning(
                            self, 
                            "Duplicate Tab", 
                            f"A tab for '{tab_data['title']}' by '{tab_data['band']}' from album '{tab_data['album']}' already exists."
                        )
                        return
                    
                    # Add to database
                    self.db_manager.add_tab(tab_data)

                    # Reload data
                    self.load_data()

                    # Show success message
                    self.statusBar().showMessage(f"Added new tab: {tab_data['title']} by {tab_data['band']}")

                except ValueError as ve:
                    # This would be thrown by our duplicate check in add_tab
                    QMessageBox.warning(self, "Duplicate Tab", str(ve))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tab: {str(e)}")

    def show_batch_add_dialog(self):
        """Show dialog to add multiple tabs at once with duplicate checking"""
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
                
                # Track statistics
                success_count = 0
                duplicate_count = 0
                error_count = 0

                # Add the tabs to the database
                for tab in tabs_data:
                    try:
                        # Check for duplicate
                        if self.db_manager.tab_exists(tab["band"], tab["album"], tab["title"]):
                            duplicate_count += 1
                            continue
                            
                        self.db_manager.add_tab(tab)
                        success_count += 1
                    except ValueError as ve:
                        # This would be our duplicate error
                        duplicate_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error adding tab {tab['title']}: {e}")

                # Refresh the table view
                self.load_data()

                # Show detailed success message
                message = f"Successfully added {success_count} tabs"
                if duplicate_count > 0:
                    message += f", {duplicate_count} duplicates skipped"
                if error_count > 0:
                    message += f", {error_count} errors"
                    
                self.statusBar().showMessage(message)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add tabs: {str(e)}")

    def delete_selected_tabs(self):
        """Delete the selected tabs"""
        try:
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
            selected_rows = selection_model.selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No rows selected.")
                return

            # Confirm deletion
            if QMessageBox.question(
                    self,
                    "Confirm Deletion",
                    f"Are you sure you want to delete {len(selected_rows)} selected tab(s)?",
                    QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                # Get proxy model and source model
                proxy_model = current_tab.model()
                source_model = proxy_model.sourceModel()

                # Collect all tab IDs to delete (from last to first to avoid index shifting)
                tab_ids = []
                for proxy_index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                    proxy_row = proxy_index.row()
                    source_index = proxy_model.mapToSource(proxy_index)
                    
                    if not source_index.isValid():
                        continue
                        
                    source_row = source_index.row()
                    # Make sure the row exists in source model data
                    if 0 <= source_row < len(source_model._data):
                        tab_id = source_model._data[source_row][0]  # Get ID from first column
                        tab_ids.append(tab_id)

                # Delete all tabs from database
                deleted_count = 0
                for tab_id in tab_ids:
                    try:
                        self.db_manager.delete_tab(tab_id)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting tab {tab_id}: {str(e)}")
                    
                # Clean up empty bands after deletion
                empty_bands_removed = 0
                try:
                    empty_bands_removed = self.db_manager.clean_up_empty_bands() or 0
                except Exception as e:
                    print(f"Error cleaning up empty bands: {str(e)}")

                # Reload data
                self.load_data()

                # Show success message
                if deleted_count > 0:
                    delete_message = f"{deleted_count} tabs deleted successfully"
                    if empty_bands_removed > 0:
                        delete_message += f", {empty_bands_removed} empty band(s) removed"
                    self.statusBar().showMessage(delete_message)
                else:
                    self.statusBar().showMessage("No tabs were deleted")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to delete tabs: {str(e)}")
            self.statusBar().showMessage("Error deleting tabs")

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

    def import_from_csv(self):
        """Import tabs from a CSV file with duplicate checking"""
        # Open file dialog to select CSV file
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            # Read CSV file
            import csv
            
            # Add debug messages
            self.statusBar().showMessage(f"Reading CSV file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8-sig') as csv_file:  # Using utf-8-sig to handle BOM
                # Read first line to determine column names
                first_line = csv_file.readline().strip()
                csv_file.seek(0)  # Go back to beginning of file
                
                # Print column names for debugging
                print(f"CSV Headers: {first_line}")
                
                # Create reader with proper handling of column names
                reader = csv.DictReader(csv_file)
                print(f"Column names detected: {reader.fieldnames}")
                
                # Count successful imports and track statistics
                success_count = 0
                error_count = 0
                duplicate_count = 0
                
                # Process each row
                for row in reader:
                    try:
                        # Debug print each row
                        print(f"Processing row: {row}")
                        
                        # Handle potential typo in 'genre' column (genrge)
                        genre = row.get('genre', '')
                        if not genre:
                            genre = row.get('genrge', '')
                        
                        # Skip empty rows
                        if not row.get('band') or not row.get('title'):
                            print("Skipping row without band or title")
                            continue
                        
                        # Extract data from row (using get to handle missing columns)
                        # Handle rating - use default 3 if empty or None
                        rating_value = row.get('rating')
                        if rating_value is None or rating_value == '':
                            rating = 1
                        else:
                            try:
                                rating = int(float(rating_value))
                            except:
                                rating = 1  # Default if conversion fails
                        
                        band = row.get('band', '').strip()
                        album = row.get('album', '').strip()
                        title = row.get('title', '').strip()
                        tuning = row.get('Tuning', row.get('tuning', '')).strip()  # Try both capitalizations
                        
                        # Check for duplicate before adding
                        if self.db_manager.tab_exists(band, album, title):
                            print(f"Duplicate found: {band} - {album} - {title}")
                            duplicate_count += 1
                            continue
                        
                        tab_data = {
                            "band": band,
                            "album": album,
                            "title": title,
                            "tuning": tuning,
                            "rating": rating,
                            "genre": genre.strip()
                        }
                        
                        print(f"Adding tab: {tab_data}")
                        
                        # Add to database
                        self.db_manager.add_tab(tab_data)
                        success_count += 1
                        
                    except ValueError as ve:
                        # This is for our duplicate check error
                        print(f"Duplicate tab: {ve}")
                        duplicate_count += 1
                        continue
                    except Exception as e:
                        print(f"Error importing row: {e}")
                        error_count += 1
                        continue
                
                # Show detailed status message
                status_msg = f"Imported {success_count} tabs"
                if duplicate_count > 0:
                    status_msg += f", {duplicate_count} duplicates skipped"
                if error_count > 0:
                    status_msg += f", {error_count} errors"
                
                # Reload data
                self.load_data()
                
                # Show success message
                self.statusBar().showMessage(status_msg)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to import CSV file: {str(e)}")