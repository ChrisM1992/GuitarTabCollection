import traceback
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QPushButton, QFormLayout, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton,
                             QButtonGroup, QMessageBox, QSizePolicy, QInputDialog,
                             QMenu, QAction)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QColor

class PitchShifterDialog(QDialog):
    """Dialog for pitch shifting calculations between guitar tunings"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pitch Calculator")
        self.setMinimumSize(650, 500)
        self.db_manager = db_manager
        
        # Common notes in order for pitch calculations
        self.all_notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Order for determining tuning direction: E -> D -> C -> B -> A -> G -> F
        # This is the specific order for determining if we tune up or down
        self.note_order = ["E", "D", "C", "B", "A", "G", "F"]
        
        # Store default tunings for 6 and 7 string guitars
        self.standard_6_string = "E A D G B E"
        self.standard_7_string = "B E A D G B E"
        
        # Initialize tuning lists
        self.tunings_6_string = [
            "E A D G B E",   # Standard
            "D A D G B E",   # Drop D
            "D G C F A D",   # Whole step down
            "C G C F A D",   # Drop C
            "A# F A# D# G C"  # Drop A#
        ]
        
        self.tunings_7_string = [
            "B E A D G B E",  # Standard 7-string
            "C F A D G B E",  # 7-string variant
            "A D G C F A D"   # Dropped 7-string
        ]
        
        # Current selection
        self.current_is_7_string = False
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Add styling for text color
        self.setStyleSheet("""
            QLabel, QRadioButton, QGroupBox, QTableWidget, QHeaderView, QComboBox {
                color: #cccccc; /* Light gray color */
            }
        """)
        
        # String selection (6 or 7 string guitar)
        string_group = QGroupBox("Guitar Type")
        string_layout = QHBoxLayout()
        
        # Radio buttons for string selection
        self.six_string_radio = QRadioButton("6-String")
        self.seven_string_radio = QRadioButton("7-String")
        self.string_button_group = QButtonGroup()
        self.string_button_group.addButton(self.six_string_radio)
        self.string_button_group.addButton(self.seven_string_radio)
        self.six_string_radio.setChecked(True)  # Default to 6-string
        
        string_layout.addWidget(self.six_string_radio)
        string_layout.addWidget(self.seven_string_radio)
        string_group.setLayout(string_layout)
        main_layout.addWidget(string_group)
        
        # Connect signals
        self.six_string_radio.toggled.connect(self.on_string_type_changed)
        
        # Tuning selection group
        tuning_group = QGroupBox("Tuning Selection")
        tuning_layout = QFormLayout()
        
        # Current tuning dropdown
        self.current_tuning_combo = QComboBox()
        self.current_tuning_combo.setMinimumWidth(300)
        self.current_tuning_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.current_tuning_combo.customContextMenuRequested.connect(self.show_tuning_context_menu)
        tuning_layout.addRow("Current Tuning:", self.current_tuning_combo)
        
        # Target tuning dropdown
        self.target_tuning_combo = QComboBox()
        self.target_tuning_combo.setMinimumWidth(300)
        self.target_tuning_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.target_tuning_combo.customContextMenuRequested.connect(self.show_tuning_context_menu)
        tuning_layout.addRow("Target Tuning:", self.target_tuning_combo)
        
        # Calculate button
        self.calculate_btn = QPushButton("Calculate Pitch Shift")
        self.calculate_btn.clicked.connect(self.calculate_pitch_shift)
        tuning_layout.addRow("", self.calculate_btn)
        
        # Add tuning button (aligned right)
        add_button_layout = QHBoxLayout()
        add_button_layout.addStretch(1)  # This pushes the button to the right
        
        self.add_tuning_btn = QPushButton("Add Tuning")
        self.add_tuning_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Only as big as needed
        self.add_tuning_btn.setStyleSheet("""
            QPushButton {
                background-color: #e3ac63;
                border: none;
                color: black;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d39b52;
            }
        """)
        self.add_tuning_btn.clicked.connect(self.add_new_tuning)
        add_button_layout.addWidget(self.add_tuning_btn)
        
        tuning_layout.addRow("", add_button_layout)
        
        tuning_group.setLayout(tuning_layout)
        main_layout.addWidget(tuning_group)
        
        # Results group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["String", "Change", "Action"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #3e3e42; }")
        
        results_layout.addWidget(self.results_table)
        
        # Summary label
        self.summary_label = QLabel("Select tunings and click Calculate to see results")
        self.summary_label.setAlignment(Qt.AlignCenter)
        results_layout.addWidget(self.summary_label)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        # Populate tuning comboboxes
        self.populate_tuning_combos()
    
    def populate_tuning_combos(self):
        """Populate tuning selection comboboxes based on guitar type"""
        # Clear existing items
        self.current_tuning_combo.clear()
        self.target_tuning_combo.clear()
        
        # Get tunings based on current selection
        tunings = self.tunings_7_string if self.current_is_7_string else self.tunings_6_string
        
        # Add to database if available
        if hasattr(self.db_manager, 'get_all_tunings'):
            db_tunings = self.db_manager.get_all_tunings(seven_string=self.current_is_7_string)
            if db_tunings:
                for tuning in db_tunings:
                    if tuning not in tunings:
                        tunings.append(tuning)
        
        # Add tunings to comboboxes
        for tuning in tunings:
            self.current_tuning_combo.addItem(tuning)
            self.target_tuning_combo.addItem(tuning)
        
        # Set defaults
        default_tuning = self.standard_7_string if self.current_is_7_string else self.standard_6_string
        
        # Find default tuning index
        current_idx = self.current_tuning_combo.findText(default_tuning)
        if current_idx >= 0:
            self.current_tuning_combo.setCurrentIndex(current_idx)
        
        # Reset results
        self.results_table.setRowCount(0)
        self.summary_label.setText("Select tunings and click Calculate to see results")
    
    def on_string_type_changed(self):
        """Handle change between 6 and 7 string guitars"""
        self.current_is_7_string = self.seven_string_radio.isChecked()
        self.populate_tuning_combos()
    
    def show_tuning_context_menu(self, position):
        """Show context menu for tuning comboboxes"""
        sender = self.sender()
        
        menu = QMenu()
        add_action = QAction("Add New Tuning", self)
        add_action.triggered.connect(self.add_new_tuning)
        
        edit_action = QAction("Edit Tuning", self)
        edit_action.triggered.connect(lambda: self.edit_tuning(sender))
        
        delete_action = QAction("Delete Tuning", self)
        delete_action.triggered.connect(lambda: self.delete_tuning(sender))
        
        menu.addAction(add_action)
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        
        menu.exec_(sender.mapToGlobal(position))
    
    def add_new_tuning(self):
        """Add a new tuning to the list"""
        is_seven_string = self.current_is_7_string
        tuning_type = "7-String" if is_seven_string else "6-String"
        
        new_tuning, ok = QInputDialog.getText(
            self,
            f"Add New {tuning_type} Tuning",
            "Enter tuning (space-separated notes, e.g. 'E A D G B E'):"
        )
        
        if ok and new_tuning:
            # Validate tuning format
            parts = new_tuning.strip().split()
            expected_count = 7 if is_seven_string else 6
            
            if len(parts) != expected_count:
                QMessageBox.warning(
                    self,
                    "Invalid Tuning",
                    f"A {tuning_type} tuning must have exactly {expected_count} notes."
                )
                return
                
            # Check if tuning already exists
            tunings_list = self.tunings_7_string if is_seven_string else self.tunings_6_string
            if new_tuning in tunings_list:
                QMessageBox.information(self, "Duplicate", "This tuning already exists.")
                return
                
            # Add to list
            if is_seven_string:
                self.tunings_7_string.append(new_tuning)
            else:
                self.tunings_6_string.append(new_tuning)
                
            # Add to database if available
            if hasattr(self.db_manager, 'add_tuning'):
                try:
                    self.db_manager.add_tuning(new_tuning, is_seven_string)
                except Exception as e:
                    print(f"Error adding tuning to database: {e}")
            
            # Refresh comboboxes
            self.populate_tuning_combos()
            
            # Select the new tuning
            index = self.current_tuning_combo.findText(new_tuning)
            if index >= 0:
                self.current_tuning_combo.setCurrentIndex(index)
    
    def edit_tuning(self, combo_box):
        """Edit the selected tuning"""
        current_tuning = combo_box.currentText()
        is_seven_string = self.current_is_7_string
        tuning_type = "7-String" if is_seven_string else "6-String"
        
        # Don't allow editing default tunings
        if current_tuning in ["E A D G B E", "B E A D G B E"]:
            QMessageBox.information(
                self,
                "Cannot Edit",
                "Standard tunings cannot be edited."
            )
            return
        
        new_tuning, ok = QInputDialog.getText(
            self,
            f"Edit {tuning_type} Tuning",
            "Edit tuning (space-separated notes):",
            text=current_tuning
        )
        
        if ok and new_tuning and new_tuning != current_tuning:
            # Validate tuning format
            parts = new_tuning.strip().split()
            expected_count = 7 if is_seven_string else 6
            
            if len(parts) != expected_count:
                QMessageBox.warning(
                    self,
                    "Invalid Tuning",
                    f"A {tuning_type} tuning must have exactly {expected_count} notes."
                )
                return
                
            # Replace in list
            tunings_list = self.tunings_7_string if is_seven_string else self.tunings_6_string
            if current_tuning in tunings_list:
                index = tunings_list.index(current_tuning)
                tunings_list[index] = new_tuning
                
            # Update in database if available
            if hasattr(self.db_manager, 'update_tuning'):
                try:
                    self.db_manager.update_tuning(current_tuning, new_tuning, is_seven_string)
                except Exception as e:
                    print(f"Error updating tuning in database: {e}")
            
            # Refresh comboboxes
            self.populate_tuning_combos()
            
            # Select the edited tuning
            index = combo_box.findText(new_tuning)
            if index >= 0:
                combo_box.setCurrentIndex(index)
    
    def delete_tuning(self, combo_box):
        """Delete the selected tuning"""
        current_tuning = combo_box.currentText()
        is_seven_string = self.current_is_7_string
        
        # Don't allow deleting default tunings
        if current_tuning in ["E A D G B E", "B E A D G B E"]:
            QMessageBox.information(
                self,
                "Cannot Delete",
                "Standard tunings cannot be deleted."
            )
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the tuning '{current_tuning}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from list
            tunings_list = self.tunings_7_string if is_seven_string else self.tunings_6_string
            if current_tuning in tunings_list:
                tunings_list.remove(current_tuning)
                
            # Remove from database if available
            if hasattr(self.db_manager, 'delete_tuning'):
                try:
                    self.db_manager.delete_tuning(current_tuning)
                except Exception as e:
                    print(f"Error deleting tuning from database: {e}")
            
            # Refresh comboboxes
            self.populate_tuning_combos()
    
    def parse_tuning(self, tuning_str):
        """Parse tuning string into list of notes"""
        return tuning_str.strip().split(" ")
    
    def parse_note(self, note):
        """Parse note from tuning (handle both formats: E or e)"""
        note = note.upper()
        
        # Check if note is in all_notes list
        if note in self.all_notes:
            return note
            
        # Handle alternate notations
        if note == "BB":
            return "A#"
        elif note == "EB":
            return "D#"
        elif note == "AB":
            return "G#"
        elif note == "DB":
            return "C#"
        elif note == "GB":
            return "F#"
            
        # If no match, return original note
        return note
    
    def calculate_pitch_shift(self):
        """Calculate pitch shift between current and target tunings"""
        try:
            # Get selected tunings
            current_tuning_str = self.current_tuning_combo.currentText()
            target_tuning_str = self.target_tuning_combo.currentText()
            
            # Parse tunings into notes
            current_notes = self.parse_tuning(current_tuning_str)
            target_notes = self.parse_tuning(target_tuning_str)
            
            # Check if number of strings match
            if len(current_notes) != len(target_notes):
                QMessageBox.warning(self, "Tuning Mismatch", 
                    f"Current tuning has {len(current_notes)} strings, but target has {len(target_notes)} strings.")
                return
                
            # Get number of strings
            num_strings = len(current_notes)
            
            # Clear previous results
            self.results_table.setRowCount(num_strings)
            
            # Determine the tuning direction by comparing notes in the specific order: E D C B A G F
            # If one note is higher than the other in this order, we tune DOWN
            # If one note is lower than the other in this order, we tune UP
            
            tuning_direction = 0  # 0 = same, -1 = tune down, 1 = tune up
            
            # Compare each pair of strings from lowest to highest until we find a difference
            for i in range(num_strings):
                current_note = self.parse_note(current_notes[i])
                target_note = self.parse_note(target_notes[i])
                
                if current_note != target_note:
                    # Check if both notes are in our order list
                    if current_note in self.note_order and target_note in self.note_order:
                        current_idx = self.note_order.index(current_note)
                        target_idx = self.note_order.index(target_note)
                        
                        # If current_idx < target_idx, we're going DOWN in the order (tuning down)
                        # If current_idx > target_idx, we're going UP in the order (tuning up)
                        if current_idx < target_idx:
                            tuning_direction = -1  # Tune DOWN
                        else:
                            tuning_direction = 1   # Tune UP
                    # Special case for notes not in our standard order (like A#)
                    elif current_note == "E" and target_note.startswith("A"):
                        # Going from E to any A note (A, A#) is always tuning DOWN
                        tuning_direction = -1  # Tune DOWN
                    else:
                        # For notes not in our order, use semitone calculation
                        semitone_diff = self.calculate_semitone_difference(current_note, target_note)
                        tuning_direction = 1 if semitone_diff > 0 else -1
                    
                    # Break after finding the first difference
                    break
            
            # Track pitch shifts and special strings
            pitch_shifts = []
            special_strings = []
            
            # Calculate the shifts based on the determined direction
            for i, (current, target) in enumerate(zip(current_notes, target_notes)):
                # Parse notes to handle different formats
                current_note = self.parse_note(current)
                target_note = self.parse_note(target)
                
                # Calculate semitone difference using chromatic scale
                semitone_diff = self.calculate_semitone_difference(current_note, target_note)
                
                # Force the direction based on our tuning_direction
                # For a given tuning change, all strings MUST move in the same direction
                if tuning_direction < 0:  # Tuning DOWN
                    # If we're tuning down but calculation is positive, make it negative
                    if semitone_diff > 0:
                        semitone_diff -= 12
                elif tuning_direction > 0:  # Tuning UP
                    # If we're tuning up but calculation is negative, make it positive
                    if semitone_diff < 0:
                        semitone_diff += 12
                else:  # No change in direction
                    # Choose smaller absolute value
                    if abs(semitone_diff) > 6:
                        if semitone_diff > 0:
                            semitone_diff = semitone_diff - 12
                        else:
                            semitone_diff = semitone_diff + 12
                            
                # Special case checks after direction adjustment
                # Ensure E to A# is always negative (tuning down)
                if current_note == "E" and target_note == "A#" and semitone_diff > 0:
                    semitone_diff -= 12
                    
                pitch_shifts.append(semitone_diff)
                
                # String number (6 is lowest/thickest, 1 is highest/thinnest for 6-string)
                string_num = num_strings - i
                
                # Set table data
                self.results_table.setItem(i, 0, QTableWidgetItem(f"String {string_num} ({current} → {target})"))
                
                # Set semitone difference with color indication
                diff_item = QTableWidgetItem(f"{semitone_diff:+d}")
                if semitone_diff == 0:
                    diff_item.setForeground(QColor("white"))
                elif semitone_diff > 0:
                    diff_item.setForeground(QColor("green"))
                else:
                    diff_item.setForeground(QColor("red"))
                self.results_table.setItem(i, 1, diff_item)
                
                # Set action text
                self.results_table.setItem(i, 2, QTableWidgetItem(self.get_action_text(semitone_diff)))
                
                # Check for special tuning cases
                if len(pitch_shifts) > 1:
                    # Find most common value
                    value_counts = {}
                    for val in pitch_shifts:
                        if val in value_counts:
                            value_counts[val] += 1
                        else:
                            value_counts[val] = 1
                    
                    # Find mode (most common value)
                    mode_value = max(value_counts.items(), key=lambda x: x[1])[0]
                    
                    if semitone_diff != mode_value:
                        special_strings.append(string_num)
            
            # Generate summary
            self.generate_summary(pitch_shifts, special_strings)
            
        except Exception:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error calculating pitch shift: {str(e)}")
    
    def calculate_semitone_difference(self, note1, note2):
        """Calculate semitone difference between two notes in chromatic scale"""
        # Get indices in the all_notes list (chromatic scale)
        idx1 = self.all_notes.index(note1)
        idx2 = self.all_notes.index(note2)
        
        # Calculate both possible differences
        direct_diff = idx2 - idx1
        
        # Handle wrap-around for shorter path
        if direct_diff > 6:
            direct_diff -= 12
        elif direct_diff < -6:
            direct_diff += 12
        
        # Handle special cases explicitly
        # For E to A#, always return negative value
        if note1 == "E" and note2 == "A#":
            return -6  # E to A# is -6 semitones when tuning down
            
        return direct_diff
    
    def get_action_text(self, diff):
        """Get descriptive text for the tuning action"""
        if diff == 0:
            return "No change"
        elif diff > 0:
            return f"Tune UP {abs(diff)} semitone{'s' if abs(diff) > 1 else ''}"
        else:
            return f"Tune DOWN {abs(diff)} semitone{'s' if abs(diff) > 1 else ''}"
    
    def generate_summary(self, pitch_shifts, special_strings):
        """Generate summary text of tuning changes"""
        if not pitch_shifts:
            return
            
        # Find most common value
        value_counts = {}
        for val in pitch_shifts:
            if val in value_counts:
                value_counts[val] += 1
            else:
                value_counts[val] = 1
        
        mode_value = max(value_counts.items(), key=lambda x: x[1])[0]
        mode_count = value_counts[mode_value]
        
        # Generate summary text
        if mode_count == len(pitch_shifts):
            # All strings change by the same amount
            summary = f"Main shift: {mode_value:+d} semitones"
            if mode_value > 0:
                summary += f" (UP {abs(mode_value)})"
            elif mode_value < 0:
                summary += f" (DOWN {abs(mode_value)})"
            else:
                summary += " (NO CHANGE)"
        else:
            # Some strings are different
            summary = f"Main shift: {mode_value:+d} semitones"
            if mode_value > 0:
                summary += f" (UP {abs(mode_value)})"
            elif mode_value < 0:
                summary += f" (DOWN {abs(mode_value)})"
            else:
                summary += " (NO CHANGE)"
                
            # Add info about special strings
            if special_strings:
                summary += f" with special tuning for strings: {', '.join(map(str, special_strings))}"
        
        # Set summary text
        self.summary_label.setText(summary)