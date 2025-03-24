from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
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
        self.tunings = []
        if hasattr(parent, 'db_manager'):
            self.tunings = parent.db_manager.get_all_tunings()
        else:
            # Fallback to hardcoded tunings
            self.tunings = ["E A D G B E", "D G C F A D", "C G C F A D", "D A D G B E", "A# F A# D# G C"]

        # Create layout
        layout = QFormLayout(self)

        # Artist selection
        self.band_combo = QComboBox()
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

        # Tuning with dropdown and add/delete options
        tuning_layout = QHBoxLayout()
        self.tuning = QComboBox()
        self.tuning.addItems(self.tunings)
        self.tuning.setEditable(True)
        self.tuning.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tuning.customContextMenuRequested.connect(self.showTuningContextMenu)
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
        new_tuning, ok = QInputDialog.getText(self, "Add New Tuning", "Enter tuning name:")
        if ok and new_tuning:
            if new_tuning not in self.tunings:
                # Add to database if parent has db_manager
                try:
                    if hasattr(self.parent(), 'db_manager'):
                        self.parent().db_manager.add_tuning(new_tuning)
                        # Update combobox
                        self.tuning.addItem(new_tuning)
                        self.tunings.append(new_tuning)
                        # Select the newly added tuning
                        self.tuning.setCurrentText(new_tuning)
                    else:
                        # Just add to combobox if no db_manager
                        self.tuning.addItem(new_tuning)
                        self.tunings.append(new_tuning)
                        self.tuning.setCurrentText(new_tuning)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tuning: {str(e)}")
            else:
                QMessageBox.information(self, "Duplicate", "This tuning already exists in the database.")

    def deleteTuning(self):
        """Delete the currently selected tuning from dropdown and database"""
        current_tuning = self.tuning.currentText()
        
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
            # Always allow deletion if no db_manager
            deleted = True
        
        # If deleted from database (or no db to delete from), remove from the combo box
        if deleted:
            index = self.tuning.currentIndex()
            if index >= 0:
                self.tuning.removeItem(index)
                if current_tuning in self.tunings:
                    self.tunings.remove(current_tuning)

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

        # Create tab data for each song
        tuning = self.tuning.currentText()
        genre = self.genre.text().strip()

        tabs_data = []
        for title in song_titles:
            tabs_data.append({
                'band': band,
                'album': album,
                'title': title,
                'tuning': tuning,
                'rating': self.rating,
                'genre': genre
            })

        return tabs_data