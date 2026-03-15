from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QLineEdit, QLabel, QDialogButtonBox,
    QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QInputDialog, QMenu,
    QAction, QMessageBox, QWidget, QTextEdit, QDateEdit
)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QColor


class StarRating(QWidget):
    """Clickable star-rating widget used in dialogs."""

    def __init__(self, parent=None, max_stars=5):
        super().__init__(parent)
        self.max_stars = max_stars
        self.current_rating = 1
        self.star_size = 24
        self.setMouseTracking(True)
        self.setMinimumHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.stars = []
        for i in range(max_stars):
            star = QPushButton()
            star.setFixedSize(QSize(self.star_size, self.star_size))
            star.setCursor(Qt.PointingHandCursor)
            star.setText("★")
            star.clicked.connect(lambda _, idx=i: self.setRating(idx + 1))
            layout.addWidget(star)
            self.stars.append(star)

        layout.addStretch()
        self.updateStars()

    def setRating(self, rating):
        self.current_rating = max(1, min(self.max_stars, int(rating)))
        self.updateStars()

    def getRating(self):
        return self.current_rating

    def updateStars(self):
        for i, star in enumerate(self.stars):
            if i < self.current_rating:
                star.setStyleSheet("""
QPushButton {
    background-color: transparent; border: none;
    color: #FFD700; font-size: 20px; padding: 0; margin: 0;
}
QPushButton:hover { color: #9932cc; }
""")
            else:
                star.setStyleSheet("""
QPushButton {
    background-color: transparent; border: none;
    color: #d3d3d3; font-size: 20px; padding: 0; margin: 0;
}
QPushButton:hover { color: #8a2be2; }
""")

    def leaveEvent(self, event):
        self.updateStars()

    def mouseMoveEvent(self, event):
        for i in range(self.max_stars):
            if event.pos().x() < (i + 1) * (self.star_size + 2):
                for j in range(self.max_stars):
                    color = "#FFD700" if j <= i else "#d3d3d3"
                    self.stars[j].setStyleSheet(f"""
QPushButton {{
    background-color: transparent; border: none;
    color: {color}; font-size: 20px; padding: 0; margin: 0;
}}
""")
                break


class AddTabDialog(QDialog):
    """Dialog for adding or editing a tab entry.

    Args:
        bands: list of existing band names.
        parent: parent widget (must expose `db_manager` for tuning management).
        show_learned_date: when True an editable date field is shown (learned view only).
        learned_date: ISO date string 'YYYY-MM-DD' to pre-fill the date field.
    """

    def __init__(self, bands, parent=None, show_learned_date=False, learned_date=None):
        super().__init__(parent)
        self.setWindowTitle("Add / Edit Tab")
        self.resize(420, 380)
        self.show_learned_date = show_learned_date

        self.standard_tunings = []
        self.seven_string_tunings = []
        if hasattr(parent, 'db_manager'):
            self.standard_tunings = parent.db_manager.get_all_tunings(seven_string=False)
            self.seven_string_tunings = parent.db_manager.get_all_tunings(seven_string=True)

        layout = QFormLayout(self)

        # ── Band ──────────────────────────────────────────────────────
        self.band_combo = QComboBox()
        self.band_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.band_combo.setMaxVisibleItems(15)
        self.band_combo.addItems(["-- New Band --"] + sorted(bands))
        self.band_combo.currentTextChanged.connect(self.onBandChanged)
        layout.addRow("Band:", self.band_combo)

        self.new_band_label = QLabel("New Band Name:")
        self.new_band = QLineEdit()
        self.new_band.setPlaceholderText("Enter new band name")
        layout.addRow(self.new_band_label, self.new_band)

        # ── Album / Title ─────────────────────────────────────────────
        self.album = QLineEdit()
        layout.addRow("Album:", self.album)

        self.title = QLineEdit()
        layout.addRow("Title:", self.title)

        # ── Tuning ────────────────────────────────────────────────────
        self.seven_string_check = QCheckBox("7-string")
        self.seven_string_check.setStyleSheet(
            "QCheckBox { color: #ff6b6b; font-weight: bold; }"
        )
        self.seven_string_check.stateChanged.connect(self.update_tunings)

        self.tuning = QComboBox()
        self.tuning.setMaxVisibleItems(15)
        self.tuning.addItems(self.standard_tunings)
        self.tuning.setEditable(True)
        self.tuning.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tuning.customContextMenuRequested.connect(self.showTuningContextMenu)

        tuning_section = QHBoxLayout()
        tuning_section.addWidget(self.seven_string_check)
        tuning_section.addWidget(self.tuning)

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

        tuning_layout = QHBoxLayout()
        tuning_layout.addLayout(tuning_section)
        tuning_layout.addLayout(tuning_buttons)
        layout.addRow("Tuning:", tuning_layout)

        # ── Rating ────────────────────────────────────────────────────
        self.rating_stars = StarRating(self)
        layout.addRow("Rating:", self.rating_stars)

        # ── Genre ─────────────────────────────────────────────────────
        self.genre = QLineEdit()
        layout.addRow("Genre:", self.genre)

        # ── Notes ─────────────────────────────────────────────────────
        self.notes = QTextEdit()
        self.notes.setFixedHeight(70)
        self.notes.setPlaceholderText("Optional notes, chords, tips…")
        layout.addRow("Notes:", self.notes)

        # ── Learned Date (only shown when editing from Learned view) ──
        if show_learned_date:
            self.learned_date_edit = QDateEdit()
            self.learned_date_edit.setCalendarPopup(True)
            self.learned_date_edit.setDisplayFormat("yyyy-MM-dd")
            if learned_date:
                try:
                    qdate = QDate.fromString(str(learned_date), "yyyy-MM-dd")
                    self.learned_date_edit.setDate(qdate if qdate.isValid() else QDate.currentDate())
                except Exception:
                    self.learned_date_edit.setDate(QDate.currentDate())
            else:
                self.learned_date_edit.setDate(QDate.currentDate())
            layout.addRow("Learned Date:", self.learned_date_edit)

        # ── Buttons ───────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.onBandChanged(self.band_combo.currentText())
        self.update_tunings()

    # ------------------------------------------------------------------
    def update_tunings(self, state=None):
        current = self.tuning.currentText()
        self.tuning.clear()
        tunings = (self.seven_string_tunings if self.seven_string_check.isChecked()
                   else self.standard_tunings)
        self.tuning.addItems(tunings)
        if current in tunings:
            self.tuning.setCurrentText(current)

    def onBandChanged(self, text):
        show = (text == "-- New Band --")
        self.new_band_label.setVisible(show)
        self.new_band.setVisible(show)

    def showTuningContextMenu(self, position):
        menu = QMenu()
        menu.addAction(QAction("Add New Tuning", self, triggered=self.addNewTuning))
        menu.addAction(QAction("Delete Tuning",  self, triggered=self.deleteTuning))
        menu.exec_(self.tuning.mapToGlobal(position))

    def addNewTuning(self):
        is_seven = self.seven_string_check.isChecked()
        new_tuning, ok = QInputDialog.getText(
            self,
            f"Add New {'7-String' if is_seven else 'Standard'} Tuning",
            "Enter tuning name:"
        )
        if not ok or not new_tuning:
            return

        current_list = self.seven_string_tunings if is_seven else self.standard_tunings
        if new_tuning in current_list:
            QMessageBox.information(self, "Duplicate", "This tuning already exists.")
            return

        try:
            if hasattr(self.parent(), 'db_manager'):
                self.parent().db_manager.add_tuning(new_tuning, is_seven)
            if is_seven:
                self.seven_string_tunings.append(new_tuning)
            else:
                self.standard_tunings.append(new_tuning)
            self.update_tunings()
            self.tuning.setCurrentText(new_tuning)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add tuning: {e}")

    def deleteTuning(self):
        current_tuning = self.tuning.currentText()
        is_seven = self.seven_string_check.isChecked()

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete tuning '{current_tuning}'?\n\nTunings used by existing tabs cannot be deleted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if hasattr(self.parent(), 'db_manager'):
            if not self.parent().db_manager.delete_tuning(current_tuning):
                QMessageBox.warning(self, "Cannot Delete",
                    "This tuning is used by existing tabs and cannot be deleted.")
                return
            if is_seven:
                self.seven_string_tunings.remove(current_tuning)
            else:
                self.standard_tunings.remove(current_tuning)
            self.update_tunings()

    def getTabData(self):
        band = self.band_combo.currentText()
        if band == "-- New Band --":
            band = self.new_band.text().strip()
            if not band:
                QMessageBox.warning(self, "Warning", "Please enter a band name.")
                return None

        title = self.title.text().strip()
        if not title:
            QMessageBox.warning(self, "Warning", "Please enter a title.")
            return None

        data = {
            "band":           band,
            "album":          self.album.text().strip(),
            "title":          title,
            "tuning":         self.tuning.currentText().strip(),
            "is_seven_string": self.seven_string_check.isChecked(),
            "rating":         self.rating_stars.getRating(),
            "genre":          self.genre.text().strip(),
            "notes":          self.notes.toPlainText().strip(),
        }

        if self.show_learned_date:
            data["learned_date"] = self.learned_date_edit.date().toString("yyyy-MM-dd")

        return data
