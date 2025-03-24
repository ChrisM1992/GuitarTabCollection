from PyQt5.QtWidgets import (QDialog, QFormLayout, QComboBox, QLineEdit,
                             QLabel, QSpinBox, QDialogButtonBox, QPushButton,
                             QHBoxLayout, QVBoxLayout, QCheckBox, QInputDialog, QMenu, QAction,
                             QMessageBox, QWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor


class StarRating(QWidget):
    """Custom widget for star rating"""
    
    def __init__(self, parent=None, max_stars=5):
        super().__init__(parent)
        self.max_stars = max_stars
        self.current_rating = 1  # Default to 1 stars
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
        
        # Get tunings from database if available
        self.standard_tunings = []
        self.seven_string_tunings = []
        
        if hasattr(parent, 'db_manager'):
            self.standard_tunings = parent.db_manager.get_all_tunings(seven_string=False)
            self.seven_string_tunings = parent.db_manager.get_all_tunings(seven_string=True)
        
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
        
        # Tuning section with 7-string checkbox
        tuning_layout = QHBoxLayout()
        
        # 7-string tunings checkbox Set Color Checkbox Font
        self.seven_string_check = QCheckBox("7-string") 
        self.seven_string_check.setStyleSheet("""
        QCheckBox { 
            color: #ff6b6b;  /* Red/Coral color */          
            font-weight: bold;
        }
        """)
        self.seven_string_check.stateChanged.connect(self.update_tunings)

        # Tuning dropdown
        self.tuning = QComboBox()
        self.tuning.addItems(self.standard_tunings)
        self.tuning.setEditable(True)
        self.tuning.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tuning.customContextMenuRequested.connect(self.showTuningContextMenu)
        
        # Layout for tuning section
        tuning_section_layout = QHBoxLayout()
        tuning_section_layout.addWidget(self.seven_string_check)
        tuning_section_layout.addWidget(self.tuning)
        
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
        
        # Combine layouts
        tuning_layout.addLayout(tuning_section_layout)
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
        self.update_tunings()

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

    def onBandChanged(self, text):
        # Show/hide new band name field
        show_new_band = (text == "-- New Band --")
        self.new_band_label.setVisible(show_new_band)
        self.new_band.setVisible(show_new_band)

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

    def addNewTuning(self):
        """Add a new tuning to the dropdown and database"""
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

    def getTabData(self):
        """Get the entered tab data"""
        band = self.band_combo.currentText()

        # If "-- New Band --" is selected, get the name from the new band field
        if band == "-- New Band --":
            band = self.new_band.text().strip()
            if not band:
                QMessageBox.warning(self, "Warning", "Please enter a band name")
                return None  # No band name entered

        # Check for required fields
        title = self.title.text().strip()
        if not title:
            QMessageBox.warning(self, "Warning", "Please enter a title")
            return None

        # Tuning management
        tuning = self.tuning.currentText().strip()
        is_seven_string = self.seven_string_check.isChecked()

        # Return the tab data with additional 7-string context
        return {
            "band": band,
            "album": self.album.text().strip(),
            "title": title,
            "tuning": tuning,
            "is_seven_string": is_seven_string,
            "rating": self.rating_stars.getRating(),
            "genre": self.genre.text().strip()
        }