from PyQt5.QtWidgets import (QDialog, QFormLayout, QComboBox, QLineEdit,
                             QLabel, QSpinBox, QDialogButtonBox, QPushButton,
                             QHBoxLayout, QVBoxLayout, QInputDialog, QMenu, QAction,
                             QMessageBox, QWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor


class StarRating(QWidget):
    """Custom widget for star rating"""
    
    def __init__(self, parent=None, max_stars=5):
        super().__init__(parent)
        self.max_stars = max_stars
        self.current_rating = 3  # Default to 3 stars
        self.star_size = 24
        self.setMouseTracking(True)
        self.setMinimumHeight(30)
        
        # Layout for the stars
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create star buttons
        self.stars = []
        for i in range(max_stars):
            star = QPushButton()
            star.setFixedSize(QSize(self.star_size, self.star_size))
            star.setCursor(Qt.PointingHandCursor)
            star.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #d3d3d3;
                    font-size: 20px;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    color: #FFD700;
                }
            """)
            star.setText("★")
            star.clicked.connect(lambda _, idx=i: self.setRating(idx + 1))
            layout.addWidget(star)
            self.stars.append(star)
        
        layout.addStretch()
        self.updateStars()
    
    def setRating(self, rating):
        """Set the current rating"""
        self.current_rating = rating
        self.updateStars()
    
    def getRating(self):
        """Get the current rating"""
        return self.current_rating
    
    def updateStars(self):
        """Update star appearance based on current rating"""
        for i, star in enumerate(self.stars):
            if i < self.current_rating:
                star.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        color: #FFD700;
                        font-size: 20px;
                        padding: 0px;
                        margin: 0px;
                    }
                    QPushButton:hover {
                        color: #9932cc;
                    }
                """)
            else:
                star.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        color: #d3d3d3;
                        font-size: 20px;
                        padding: 0px;
                        margin: 0px;
                    }
                    QPushButton:hover {
                        color: #8a2be2;
                    }
                """)
            
    def enterEvent(self, event):
        """Handle mouse enter event"""
        self.setMouseTracking(True)
        
    def leaveEvent(self, event):
        """Handle mouse leave event"""
        self.updateStars()
        
    def mouseMoveEvent(self, event):
        """Handle mouse move for preview"""
        for i in range(self.max_stars):
            if event.pos().x() < (i + 1) * self.star_size:
                # Preview rating
                for j in range(self.max_stars):
                    if j <= i:
                        self.stars[j].setStyleSheet("""
                            QPushButton {
                                background-color: transparent;
                                border: none;
                                color: #FFD700;
                                font-size: 20px;
                                padding: 0px;
                                margin: 0px;
                            }
                        """)
                    else:
                        self.stars[j].setStyleSheet("""
                            QPushButton {
                                background-color: transparent;
                                border: none;
                                color: #d3d3d3;
                                font-size: 20px;
                                padding: 0px;
                                margin: 0px;
                            }
                        """)
                break


class AddTabDialog(QDialog):
    """Dialog for adding a new tab entry"""

    def __init__(self, bands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Tab")
        self.resize(400, 300)
        
        # List of common guitar tunings
        self.tunings = ["E A D G B E", "D A D G B E", "C G C F A D", "D G D G B D", "E B E G# B E", "D A D F# A D"]
        self.default_tunings = list(self.tunings)  # Store defaults to prevent deletion

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
        
        # Tuning with dropdown and buttons
        tuning_layout = QHBoxLayout()
        self.tuning = QComboBox()
        self.tuning.addItems(self.tunings)
        self.tuning.setEditable(True)
        self.tuning.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tuning.customContextMenuRequested.connect(self.showTuningContextMenu)
        tuning_layout.addWidget(self.tuning)
        
        # Add/Remove tuning buttons
        tuning_buttons = QHBoxLayout()
        add_tuning_btn = QPushButton("+")
        add_tuning_btn.setFixedSize(25, 25)
        add_tuning_btn.setToolTip("Add new tuning")
        add_tuning_btn.clicked.connect(self.addNewTuning)
        tuning_buttons.addWidget(add_tuning_btn)
        
        remove_tuning_btn = QPushButton("×")
        remove_tuning_btn.setFixedSize(25, 25)
        remove_tuning_btn.setToolTip("Delete selected tuning")
        remove_tuning_btn.clicked.connect(self.deleteTuning)
        tuning_buttons.addWidget(remove_tuning_btn)
        
        tuning_layout.addLayout(tuning_buttons)
        
        # Rating stars
        self.rating_stars = StarRating(self)
        
        self.genre = QLineEdit()

        layout.addRow("Album:", self.album)
        layout.addRow("Title:", self.title)
        layout.addRow("Tuning:", tuning_layout)
        layout.addRow("Rating:", self.rating_stars)
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
        
    def addNewTuning(self):
        """Add a new tuning to the dropdown"""
        new_tuning, ok = QInputDialog.getText(self, "Add New Tuning", "Enter tuning name:")
        if ok and new_tuning:
            if new_tuning not in self.tunings:
                self.tuning.addItem(new_tuning)
                self.tunings.append(new_tuning)
                # Select the newly added tuning
                self.tuning.setCurrentText(new_tuning)
                
    def deleteTuning(self):
        """Delete the currently selected tuning"""
        current_tuning = self.tuning.currentText()
        
        # Prevent deletion of default tunings
        if current_tuning in self.default_tunings:
            QMessageBox.information(self, "Cannot Delete", 
                                    "Default tunings cannot be deleted.")
            return
            
        # Remove from the combo box and the list
        index = self.tuning.currentIndex()
        if index >= 0:
            self.tuning.removeItem(index)
            if current_tuning in self.tunings:
                self.tunings.remove(current_tuning)
                
    def showTuningContextMenu(self, position):
        """Show context menu for right-click on tuning combo box"""
        menu = QMenu()
        current_tuning = self.tuning.currentText()
        
        delete_action = QAction("Delete Tuning", self)
        delete_action.triggered.connect(self.deleteTuning)
        delete_action.setEnabled(current_tuning not in self.default_tunings)
        
        menu.addAction(delete_action)
        menu.exec_(self.tuning.mapToGlobal(position))

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
            "tuning": self.tuning.currentText().strip(),
            "rating": self.rating_stars.getRating(),
            "genre": self.genre.text().strip()
        }