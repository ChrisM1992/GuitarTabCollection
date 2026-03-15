from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QLineEdit, QLabel, QDialogButtonBox,
    QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QInputDialog, QMenu,
    QAction, QMessageBox, QWidget, QTextEdit, QDateEdit
)
from PyQt5.QtCore import Qt, QSize, QDate, QTimer
from PyQt5.QtGui import QColor
from title_checker import TitleChecker


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

    def __init__(self, bands, parent=None, show_learned_date=False, learned_date=None,
                 auto_verify=False):
        super().__init__(parent)
        self.setWindowTitle("Add / Edit Tab")
        self.resize(420, 380)
        self.show_learned_date = show_learned_date
        self._auto_verify = auto_verify
        self._checker = TitleChecker(self)

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
        self._album_lookup_btn = QPushButton("?")
        self._album_lookup_btn.setFixedSize(25, 25)
        self._album_lookup_btn.setToolTip("Look up album via MusicBrainz")
        self._album_lookup_btn.clicked.connect(self._lookup_album)
        album_row = QHBoxLayout()
        album_row.addWidget(self.album)
        album_row.addWidget(self._album_lookup_btn)
        layout.addRow("Album:", album_row)

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

        self._tuning_lookup_btn = QPushButton("?")
        self._tuning_lookup_btn.setFixedSize(25, 25)
        self._tuning_lookup_btn.setToolTip("Look up tuning via MusicBrainz")
        self._tuning_lookup_btn.clicked.connect(self._lookup_tuning)
        tuning_buttons.addWidget(self._tuning_lookup_btn)

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

        # ── Status label (shown during MusicBrainz verification) ──────
        self._verify_status = QLabel("")
        self._verify_status.setAlignment(Qt.AlignCenter)
        self._verify_status.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        layout.addRow("", self._verify_status)

        # ── Buttons ───────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_btn = buttons.button(QDialogButtonBox.Ok)
        if auto_verify:
            self._ok_btn.setText("Verify && Add")
            buttons.accepted.connect(self._verify_and_accept)
        else:
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

    def _current_band(self):
        if self.band_combo.currentText() == "-- New Band --":
            return self.new_band.text().strip()
        return self.band_combo.currentText()

    def _lookup_album(self):
        band  = self._current_band()
        title = self.title.text().strip()
        if not band or not title:
            QMessageBox.information(self, "Lookup", "Enter a band and title first.")
            return
        self._album_lookup_btn.setText("…")
        self._album_lookup_btn.setEnabled(False)

        def _on_done(b, t, tid, data):
            self._album_lookup_btn.setText("?")
            self._album_lookup_btn.setEnabled(True)
            album = data.get("album", "")
            if not album:
                self._album_lookup_btn.setToolTip("No album suggestion found")
                return
            if not self.album.text().strip():
                self.album.setText(album)
            else:
                self._album_lookup_btn.setToolTip(f"Suggestion: {album}")

        self._checker.check(band, title, 0, "album", _on_done)

    def _lookup_tuning(self):
        band  = self._current_band()
        title = self.title.text().strip()
        if not band or not title:
            QMessageBox.information(self, "Lookup", "Enter a band and title first.")
            return
        self._tuning_lookup_btn.setText("…")
        self._tuning_lookup_btn.setEnabled(False)

        def _on_done(b, t, tid, data):
            self._tuning_lookup_btn.setText("?")
            self._tuning_lookup_btn.setEnabled(True)
            tuning = data.get("tuning", "")
            if not tuning:
                self._tuning_lookup_btn.setToolTip("No tuning suggestion found")
                return
            if not self.tuning.currentText().strip():
                self.tuning.setCurrentText(tuning)
            else:
                self._tuning_lookup_btn.setToolTip(f"Suggestion: {tuning}")

        self._checker.check(band, title, 0, "tuning", _on_done)

    # ------------------------------------------------------------------
    # Verify & Add flow  (only active when auto_verify=True)
    # ------------------------------------------------------------------
    def _verify_and_accept(self):
        band  = self._current_band()
        title = self.title.text().strip()
        if not band:
            QMessageBox.warning(self, "Warning", "Please enter a band name.")
            return
        if not title:
            QMessageBox.warning(self, "Warning", "Please enter a title.")
            return

        self._ok_btn.setEnabled(False)
        self._verify_status.setText("⟳  Verifying title via MusicBrainz…")
        self._checker.check(band, title, 0, "full", self._on_title_verified)

    def _on_title_verified(self, band, title, _tab_id, data):
        if not self.isVisible():
            return
        try:
            sug_title = data.get('title', '')
            sug_band  = data.get('band',  '')
            # Case-sensitive title comparison so capitalisation fixes are caught
            title_diff = bool(sug_title and sug_title != title)
            band_diff  = bool(sug_band  and sug_band.lower() != band.lower())

            if title_diff or band_diff:
                lines = ["MusicBrainz found a possible correction:\n"]
                if band_diff:
                    lines.append(f"  Band:    {band}  →  {sug_band}")
                if title_diff:
                    lines.append(f"  Title:   {title}  →  {sug_title}")
                lines.append("\nApply these suggestions?")

                reply = QMessageBox.question(
                    self, "Verify Title",
                    "\n".join(lines),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes:
                    if band_diff:
                        if self.band_combo.currentText() == "-- New Band --":
                            self.new_band.setText(sug_band)
                        else:
                            idx = self.band_combo.findText(sug_band, Qt.MatchFixedString)
                            if idx >= 0:
                                self.band_combo.setCurrentIndex(idx)
                            else:
                                self.band_combo.setCurrentIndex(0)
                                self.new_band.setText(sug_band)
                    if title_diff:
                        self.title.setText(sug_title)
        except Exception as e:
            print(f"[title_verify] error: {e}")

        # Always proceed to album lookup, even if title check above failed
        if not self.isVisible():
            return
        current_band  = self._current_band()
        current_title = self.title.text().strip()
        self._verify_status.setText("⟳  Looking up album…")
        try:
            self._checker.check(current_band, current_title, 0, "album", self._on_album_verified)
        except Exception as e:
            print(f"[album_lookup] error: {e}")
            self._verify_status.setText("")
            self._ok_btn.setEnabled(True)
            QMessageBox.warning(self, "Lookup Error",
                                "Could not reach MusicBrainz. Please enter album manually.")
            self.accept()

    def _on_album_verified(self, _band, _title, _tab_id, data):
        if not self.isVisible():
            return
        self._verify_status.setText("")
        self._ok_btn.setEnabled(True)
        try:
            sug_album     = data.get('album', '')
            current_album = self.album.text().strip()

            if sug_album and not current_album:
                # Clean find — auto-fill silently
                self.album.setText(sug_album)

            elif not sug_album and not current_album:
                # Nothing found — ask user; Cancel means "add without album"
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Album Not Found")
                dlg.setText(
                    "MusicBrainz couldn't find an album for this track.\n"
                    "What would you like to do?"
                )
                btn_manual  = dlg.addButton("Enter manually…", QMessageBox.AcceptRole)
                btn_skip    = dlg.addButton("Add without album", QMessageBox.DestructiveRole)
                btn_cancel  = dlg.addButton("Cancel add", QMessageBox.RejectRole)
                dlg.setDefaultButton(btn_manual)
                dlg.exec_()
                clicked = dlg.clickedButton()
                if clicked == btn_cancel:
                    return  # do NOT call accept — user cancelled the whole add
                if clicked == btn_manual:
                    album, ok = QInputDialog.getText(
                        self, "Enter Album", "Album name:"
                    )
                    if ok:
                        self.album.setText(album.strip())

            elif sug_album and current_album and sug_album.lower() != current_album.lower():
                # Suggestion differs from what user already typed — offer it
                reply = QMessageBox.question(
                    self, "Album Suggestion",
                    f"MusicBrainz suggests:\n  {sug_album}\n\n"
                    f"You entered:\n  {current_album}\n\nUse the suggestion?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    self.album.setText(sug_album)

        except Exception as e:
            print(f"[album_verify] error: {e}")

        self.accept()

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
