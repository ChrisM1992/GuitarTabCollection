from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QPushButton, QFormLayout, QGroupBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton,
                             QButtonGroup, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont

class PitchShifterDialog(QDialog):
    """Dialog for pitch shifting calculations between guitar tunings"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guitar Pitch Shifter")
        self.setMinimumSize(650, 500)
        self.db_manager = db_manager
        
        # Common notes in order for pitch calculations
        self.all_notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
         # Comprehensive stylesheet for all text elements
        self.setStyleSheet("""
            /* Set all text to light gray */
            * {
                color: #cccccc;
            }
            
            /* Group box specific styling */
            QGroupBox {
                color: #cccccc;
                font-weight: bold;
            }
            
            QGroupBox::title {
                color: #cccccc;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
            
            /* Keep special colors for the results table */
            QTableWidget::item {
                color: #cccccc;
            }
            
            /* Push button text */
            QPushButton {
                color: #cccccc;
            }
            
            /* Dropdown text */
            QComboBox, QComboBox QAbstractItemView {
                color: #cccccc;
            }
        """)


        # Store standard tunings for 6 and 7 string guitars
        self.standard_6_string = "E A D G B E"
        self.standard_7_string = "B E A D G B E"
        
        # Initialize and populate tuning database
        self.tunings_6_string = self.get_6_string_tunings()
        self.tunings_7_string = self.get_7_string_tunings()
        
        # Current selection
        self.current_is_7_string = False
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
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
        tuning_layout.addRow("Current Tuning:", self.current_tuning_combo)
        
        # Target tuning dropdown
        self.target_tuning_combo = QComboBox()
        self.target_tuning_combo.setMinimumWidth(300)
        tuning_layout.addRow("Target Tuning:", self.target_tuning_combo)
        
        # Calculate button
        self.calculate_btn = QPushButton("Calculate Pitch Shift")
        self.calculate_btn.clicked.connect(self.calculate_pitch_shift)
        tuning_layout.addRow("", self.calculate_btn)
        
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
    
    def get_6_string_tunings(self):
        """Get list of common 6-string tunings (name and notes)"""
        tunings = []
        
        # Try to get tunings from database
        if hasattr(self.db_manager, 'get_all_tunings'):
            db_tunings = self.db_manager.get_all_tunings(seven_string=False)
            if db_tunings:
                for tuning in db_tunings:
                    tunings.append(tuning)
        
        # Add common tunings if not already in list
        common_tunings = [
            "E A D G B E",  # Standard
            "D G C F A D",   # Whole step down
            "C G C F A D",   # Drop C
            "D A D G B E",   # Drop D
            "C# G# C# F# A# D#",  # Half step down
            "C F A# D# G C",  # Two steps down
            "B E A D F# B",   # Baritone
            "B F# B E G# C#",  # Open B
            "C G C G C E",    # Open C
            "D A D F# A D",   # Open D
            "E B E G# B E",   # Open E
            "A E A E A C#",   # Open A
            "G D G B D G",    # Open G
            "D A D G B D",    # DADGAD
        ]
        
        for tuning in common_tunings:
            if tuning not in tunings:
                tunings.append(tuning)
        
        return tunings
    
    def get_7_string_tunings(self):
        """Get list of common 7-string tunings (name and notes)"""
        tunings = []
        
        # Try to get tunings from database
        if hasattr(self.db_manager, 'get_all_tunings'):
            db_tunings = self.db_manager.get_all_tunings(seven_string=True)
            if db_tunings:
                for tuning in db_tunings:
                    tunings.append(tuning)
        
        # Add common tunings if not already in list
        common_tunings = [
            "B E A D G B E",   # Standard 7-string
            "A D G C F A D",   # Whole step down 7-string
            "A E A D G B E",   # Drop A 7-string
            "G C F A# D# G C",  # Drop G 7-string
            "A# D# G# C# F# A# D#",  # Half-step down 7-string
            "G D G C F A D",   # Drop G standard 7-string
            "F# B E A D G B",   # Baritone 7-string
            "G C F Bb Eb G C",  # Two steps down 7-string
        ]
        
        for tuning in common_tunings:
            if tuning not in tunings:
                tunings.append(tuning)
        
        return tunings
    
    def populate_tuning_combos(self):
        """Populate tuning selection comboboxes based on guitar type"""
        # Clear existing items
        self.current_tuning_combo.clear()
        self.target_tuning_combo.clear()
        
        # Get tunings based on current selection
        tunings = self.tunings_7_string if self.current_is_7_string else self.tunings_6_string
        
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
    
    def parse_tuning(self, tuning_str):
        """Parse tuning string into list of notes"""
        return tuning_str.strip().split(" ")
    
    def get_semitone_difference(self, note1, note2):
        """Calculate semitone difference between two notes"""
        # Get indices in the all_notes list
        idx1 = self.all_notes.index(note1)
        idx2 = self.all_notes.index(note2)
        
        # Calculate semitone difference
        diff = idx2 - idx1
        
        # Handle wrap-around (e.g. from B to C)
        if diff > 6:
            diff -= 12  # Octave down
        elif diff < -6:
            diff += 12  # Octave up
        
        return diff
    
    def get_action_text(self, diff):
        """Get descriptive text for the tuning action"""
        if diff == 0:
            return "No change"
        elif diff > 0:
            return f"Tune UP {abs(diff)} semitone{'s' if abs(diff) > 1 else ''}"
        else:
            return f"Tune DOWN {abs(diff)} semitone{'s' if abs(diff) > 1 else ''}"
    
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
            
            # Clear previous results
            self.results_table.setRowCount(len(current_notes))
            
            # Track consistent pitch shift and exceptions
            pitch_shifts = []
            special_strings = []
            
            # Calculate difference for each string
            for i, (current, target) in enumerate(zip(current_notes, target_notes)):
                # Parse notes to handle different formats
                current_note = self.parse_note(current)
                target_note = self.parse_note(target)
                
                # Calculate semitone difference
                diff = self.get_semitone_difference(current_note, target_note)
                pitch_shifts.append(diff)
                
                # String number (reversed for guitar - low to high)
                string_num = len(current_notes) - i
                
                # Set table data
                self.results_table.setItem(i, 0, QTableWidgetItem(f"String {string_num} ({current} → {target})"))
                
                # Set semitone difference with color indication
                diff_item = QTableWidgetItem(f"{diff:+d}")
                if diff == 0:
                    diff_item.setForeground(Qt.white)
                elif diff > 0:
                    diff_item.setForeground(Qt.green)
                else:
                    diff_item.setForeground(Qt.red)
                self.results_table.setItem(i, 1, diff_item)
                
                # Set action text
                self.results_table.setItem(i, 2, QTableWidgetItem(self.get_action_text(diff)))
                
                # Check for special tuning cases
                mode_value = max(set(pitch_shifts), key=pitch_shifts.count)
                if diff != mode_value:
                    special_strings.append(string_num)
            
            # Generate summary
            self.generate_summary(pitch_shifts, special_strings)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error calculating pitch shift: {str(e)}")
    
    def generate_summary(self, pitch_shifts, special_strings):
        """Generate summary text of tuning changes"""
        # Get the most common pitch shift
        if not pitch_shifts:
            return
            
        # Find most common value
        mode_value = max(set(pitch_shifts), key=pitch_shifts.count)
        mode_count = pitch_shifts.count(mode_value)
        
        # Generate summary text
        if mode_count == len(pitch_shifts):
            # All strings change by the same amount
            summary = f"All strings tune {mode_value:+d} semitones"
            if mode_value > 0:
                summary += f" (UP {abs(mode_value)})"
            elif mode_value < 0:
                summary += f" (DOWN {abs(mode_value)})"
            else:
                summary += " (NO CHANGE)"
        else:
            # Some strings are different
            if mode_count > 1:
                summary = f"Main shift: {mode_value:+d} semitones"
                if mode_value > 0:
                    summary += f" (UP {abs(mode_value)})"
                elif mode_value < 0:
                    summary += f" (DOWN {abs(mode_value)})"
                else:
                    summary += " (NO CHANGE)"
            else:
                summary = "Non-standard tuning shift"
                
            if special_strings:
                summary += f" with special tuning for strings: {', '.join(map(str, special_strings))}"
                
                # Identify drop/raised tuning patterns
                if len(special_strings) == 1 and special_strings[0] == len(pitch_shifts):
                    # Check if lowest string is tuned differently
                    lowest_diff = pitch_shifts[-1]
                    if lowest_diff < mode_value:
                        summary += f" (Drop tuning, {abs(lowest_diff - mode_value)} semitones lower)"
                    else:
                        summary += f" (Raised tuning, {abs(lowest_diff - mode_value)} semitones higher)"
        
        # Set summary text
        self.summary_label.setText(summary)
    
    def accept(self):
        """Override accept to add custom behavior"""
        super().accept()
    
    def mousePressEvent(self, event):
        """Handle mouse press events for dragging the dialog"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging the dialog"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPos() - self.drag_position)
            event.accept()

# Function to add to GuitarTabsApp class
def show_pitch_shifter(self):
    """Show the pitch shifter dialog"""
    dialog = PitchShifterDialog(self.db_manager, self)
    dialog.exec_()