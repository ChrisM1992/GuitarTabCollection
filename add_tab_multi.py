from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QLineEdit, QCheckBox, QTextEdit, QFormLayout,
                             QDialogButtonBox, QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt


class BatchAddDialog(QDialog):
    def __init__(self, bands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Add Tabs")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Store bands list
        self.bands = bands

        # Get tunings from database if available
        self.standard_tunings = []
        self.seven_string_tunings = []
        if hasattr(parent, 'db_manager'):
            self.standard_tunings = parent.db_manager.get_all_tunings(seven_string=False)
            self.seven_string_tunings = parent.db_manager.get_all_tunings(seven_string=True)
        
        # Create layout
        layout = QFormLayout(self)

        # Artist selection
        self.band_combo = QComboBox()
        self.band_combo.setMaxVisibleItems(15)
        self.band_combo.addItems(["-- New Band --"] + sorted(bands))
        self.band_combo.currentTextChanged.connect(self.onBandChanged)
        layout.addRow("Artist:", self.band_combo)

        # New band name field (initially hidden)
        self.new_band = QLineEdit()
        self.new_band.setPlaceholderText("Enter new band name")
        self.new_band_label = QLabel("New Band Name:")
        layout.addRow(self.new_band_label, self.new_band)

        # Album name
        self.album = QLineEdit()
        layout.addRow("Album:", self.album)

        # Songs list as text box
        songs_label = QLabel("Songs (one per line):")
        self.songs_text = QTextEdit()
        self.songs_text.setPlaceholderText("Enter one song title per line")
        layout.addRow(songs_label, self.songs_text)

        # 7-string tunings checkbox
        self.seven_string_check = QCheckBox("7-string")
        self.seven_string_check.stateChanged.connect(self.update_tunings)

        # Tuning with dropdown and add/delete options
        tuning_layout = QHBoxLayout()
        self.tuning = QComboBox()
        self.tuning.setMaxVisibleItems(15)
        self.tuning.addItems(self.standard_tunings)
        self.tuning.setEditable(True)
        self.tuning.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tuning.customContextMenuRequested.connect(self.showTuningContextMenu)
        tuning_layout.addWidget(self.seven_string_check)
        tuning_layout.addWidget(self.tuning)

        # Add/Remove tuning buttons
        tuning_buttons = QHBoxLayout()
        
        # Add tuning button
        add_tuning_btn = QPushButton("+")
        add_tuning_btn.setFixedSize(25, 25)
        add_tuning_btn.setToolTip("Add new tuning")
        add_tuning_btn.clicked.connect(self.addNewTuning)
        tuning_buttons.addWidget(add_tuning_btn)
        
        # Delete tuning button
        remove_tuning_btn = QPushButton("×")
        remove_tuning_btn.setFixedSize(25, 25)
        remove_tuning_btn.setToolTip("Delete selected tuning")
        remove_tuning_btn.clicked.connect(self.deleteTuning)
        tuning_buttons.addWidget(remove_tuning_btn)
        
        tuning_layout.addLayout(tuning_buttons)

        layout.addRow("Tuning:", tuning_layout)

        # Rating (default)
        self.rating = 1

        # Genre
        self.genre = QLineEdit()
        layout.addRow("Genre:", self.genre)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

        # Initial state
        self.onBandChanged(self.band_combo.currentText())

    def update_tunings(self, state=None):
        """Update tuning dropdown based on 7-string checkbox"""
        # Store current text to try to preserve it if possible
        current_text = self.tuning.currentText()
        
        # Clear and repopulate tuning dropdown
        self.tuning.clear()
        tunings = (self.seven_string_tunings if self.seven_string_check.isChecked() 
                   else self.standard_tunings)
        
        # Add tunings to dropdown
        self.tuning.addItems(tunings)
        
        # Try to restore previous text if it exists in the new list
        if current_text in tunings:
            self.tuning.setCurrentText(current_text)

    def showTuningContextMenu(self, position):
        """Show context menu for right-click on tuning combo box"""
        menu = QMenu()
        current_tuning = self.tuning.currentText()
        
        add_action = QAction("Add New Tuning", self)
        add_action.triggered.connect(self.addNewTuning)
        
        delete_action = QAction("Delete Tuning", self)
        delete_action.triggered.connect(self.deleteTuning)
        
        menu.addAction(add_action)
        menu.addAction(delete_action)
        menu.exec_(self.tuning.mapToGlobal(position))

    def onBandChanged(self, text):
        """Show/hide new band name field"""
        show_new_band = (text == "-- New Band --")
        self.new_band_label.setVisible(show_new_band)
        self.new_band.setVisible(show_new_band)

    def addNewTuning(self):
        """Add a new tuning to the dropdown"""
        is_seven_string = self.seven_string_check.isChecked()
        new_tuning, ok = QInputDialog.getText(
            self, 
            f"Add New {'7-String' if is_seven_string else 'Standard'} Tuning", 
            "Enter tuning name:"
        )
        
        if ok and new_tuning:
            # Check against current tuning list
            current_tunings = (self.seven_string_tunings if is_seven_string 
                               else self.standard_tunings)
            
            if new_tuning not in current_tunings:
                # Add to database if parent has db_manager
                try:
                    if hasattr(self.parent(), 'db_manager'):
                        self.parent().db_manager.add_tuning(new_tuning, is_seven_string)
                        
                        # Update local tuning lists
                        if is_seven_string:
                            self.seven_string_tunings.append(new_tuning)
                        else:
                            self.standard_tunings.append(new_tuning)
                        
                        # Update dropdown
                        self.update_tunings()
                        self.tuning.setCurrentText(new_tuning)
                    else:
                        # Just add to current list if no db_manager
                        if is_seven_string:
                            self.seven_string_tunings.append(new_tuning)
                        else:
                            self.standard_tunings.append(new_tuning)
                        
                        self.update_tunings()
                        self.tuning.setCurrentText(new_tuning)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tuning: {str(e)}")
            else:
                QMessageBox.information(self, "Duplicate", "This tuning already exists in the database.")

    def deleteTuning(self):
        """Delete the currently selected tuning from dropdown and database"""
        current_tuning = self.tuning.currentText()
        is_seven_string = self.seven_string_check.isChecked()
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete the tuning '{current_tuning}'?\n\nNote: Tunings used by existing tabs cannot be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        deleted = False
        # Delete from database if parent has db_manager
        if hasattr(self.parent(), 'db_manager'):
            deleted = self.parent().db_manager.delete_tuning(current_tuning)
            
            if not deleted:
                QMessageBox.warning(self, "Cannot Delete", 
                                    "This tuning cannot be deleted because it is being used by existing tabs.")
                return
            else:
                # Remove the tuning from the respective list
                if is_seven_string:
                    self.seven_string_tunings.remove(current_tuning)
                else:
                    self.standard_tunings.remove(current_tuning)
                
                # Refresh the tuning dropdown
                self.update_tunings()

    def getTabsData(self):
        """Get the data for all tabs to be added"""
        # Get band name
        band = self.band_combo.currentText()
        if band == "-- New Band --":
            band = self.new_band.text().strip()
            if not band:
                QMessageBox.warning(self, "Warning", "Please enter a band name")
                return []

        # Get album name
        album = self.album.text().strip()
        if not album:
            QMessageBox.warning(self, "Warning", "Please enter an album name")
            return []

        # Get song titles from text box
        song_text = self.songs_text.toPlainText().strip()
        if not song_text:
            QMessageBox.warning(self, "Warning", "Please enter at least one song title")
            return []

        # Split text into lines and remove empty lines
        song_titles = [line.strip() for line in song_text.split('\n') if line.strip()]

        # Get tuning and 7-string status
        tuning = self.tuning.currentText()
        is_seven_string = self.seven_string_check.isChecked()

        # Get genre
        genre = self.genre.text().strip()

        # Create tab data for each song
        tabs_data = []
        for title in song_titles:
            tabs_data.append({
                'band': band,
                'album': album,
                'title': title,
                'tuning': tuning,
                'is_seven_string': is_seven_string,
                'rating': self.rating,
                'genre': genre
            })

        return tabs_data