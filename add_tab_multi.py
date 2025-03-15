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

        # Common tunings
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

        # Tuning with dropdown and add option
        tuning_layout = QHBoxLayout()
        self.tuning = QComboBox()
        self.tuning.addItems(self.tunings)
        self.tuning.setEditable(True)
        tuning_layout.addWidget(self.tuning)

        # Add tuning button
        add_tuning_btn = QPushButton("+")
        add_tuning_btn.setFixedSize(25, 25)
        add_tuning_btn.setToolTip("Add new tuning")
        add_tuning_btn.clicked.connect(self.addNewTuning)
        tuning_layout.addWidget(add_tuning_btn)

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
                # Add to database
                try:
                    self.parent().db_manager.add_tuning(new_tuning)
                    # Update combobox
                    self.tuning.addItem(new_tuning)
                    self.tunings.append(new_tuning)
                    # Select the newly added tuning
                    self.tuning.setCurrentText(new_tuning)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tuning: {str(e)}")

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