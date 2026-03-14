import os
import sys
import csv
import shutil
import traceback
import webbrowser
import urllib.parse
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QComboBox, QLabel, QLineEdit, QHeaderView, QTabWidget,
    QMessageBox, QFileDialog, QDialog, QFormLayout, QDialogButtonBox,
    QMenu, QSizePolicy, QStyledItemDelegate, QShortcut
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QItemSelectionModel, QEvent
from PyQt5.QtGui import QColor, QKeySequence, QFont

from tabs_data_model import TabsDataModel
from database_manager import DatabaseManager
from add_tab_dialog import AddTabDialog, StarRating
from add_tab_multi import BatchAddDialog
from pitch_shifter import PitchShifterDialog


# ---------------------------------------------------------------------------
# Ultimate Guitar column delegate
# ---------------------------------------------------------------------------
class UltimateGuitarDelegate(QStyledItemDelegate):

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window

    def paint(self, painter, option, index):
        painter.save()
        bg = QColor("#eaa13f") if option.state & 0x2000 else QColor("#e3ac63")
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 4, 4)
        painter.setPen(QColor("#000000"))
        painter.drawText(option.rect.adjusted(4, 4, -4, -4), Qt.AlignCenter, "Open")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            source_model = model.sourceModel()
            source_row = model.mapToSource(index).row()
            band  = source_model._data[source_row][1]
            title = source_model._data[source_row][3]
            self._main_window.searchTabOnline(band, title)
            return True
        return super().editorEvent(event, model, option, index)


# ---------------------------------------------------------------------------
# Inline star rating delegate  ← NEW Round 2
# ---------------------------------------------------------------------------
class StarRatingDelegate(QStyledItemDelegate):
    """Click a star cell to instantly update the rating without opening a dialog."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window

    def paint(self, painter, option, index):
        painter.save()

        # Background — respect selection and alternating rows (dark theme)
        if option.state & 0x0002:  # State_Selected
            painter.fillRect(option.rect, option.palette.highlight())
        elif index.row() % 2 == 1:
            painter.fillRect(option.rect, QColor("#2a2a2d"))
        else:
            painter.fillRect(option.rect, QColor("#202022"))

        # Get numeric rating from source data
        try:
            source_model = index.model().sourceModel()
            source_row   = index.model().mapToSource(index).row()
            rating = int(source_model._data[source_row][5])
        except Exception:
            rating = 0

        # Draw filled/empty stars
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)
        cell_w = option.rect.width()
        star_w = cell_w / 5

        for i in range(5):
            star_rect = option.rect.adjusted(int(i * star_w), 1, 0, -1)
            star_rect.setWidth(int(star_w))
            char = "★" if i < rating else "☆"
            color = QColor("#FFD700") if i < rating else QColor("#aaaaaa")
            painter.setPen(color)
            painter.drawText(star_rect, Qt.AlignCenter, char)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            source_model = model.sourceModel()
            source_row   = model.mapToSource(index).row()
            tab_id       = source_model._data[source_row][0]

            x         = event.pos().x() - option.rect.x()
            star_w    = option.rect.width() / 5
            new_rating = min(5, max(1, int(x / star_w) + 1))

            try:
                self._mw.db_manager.update_rating(tab_id, new_rating)
                self._mw.load_data(preserve_tab=True)
                stars = "★" * new_rating + "☆" * (5 - new_rating)
                self._mw.statusBar().showMessage(
                    f"Rating updated to {stars}"
                )
            except Exception as e:
                print(f"Inline rating error: {e}")
            return True
        return super().editorEvent(event, model, option, index)


# ---------------------------------------------------------------------------
# Bulk Set Rating dialog
# ---------------------------------------------------------------------------
class SetRatingDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Rating")
        self.setFixedWidth(260)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select new rating for all selected tabs:"))
        self.rating_stars = StarRating(self)
        self.rating_stars.setRating(3)
        layout.addWidget(self.rating_stars)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getRating(self):
        return self.rating_stars.getRating()


# ---------------------------------------------------------------------------
# Advanced filter dialog
# ---------------------------------------------------------------------------
class AdvancedFilterDialog(QDialog):

    def __init__(self, bands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Filter")
        self.setMinimumWidth(300)
        layout = QFormLayout(self)

        self.band_filter = QComboBox()
        self.band_filter.addItem("Any")
        self.band_filter.addItems(sorted(bands))
        layout.addRow("Band:", self.band_filter)

        self.album_filter = QLineEdit()
        layout.addRow("Album:", self.album_filter)

        self.rating_filter = QComboBox()
        self.rating_filter.addItems(["Any", "1+", "2+", "3+", "4+", "5"])
        layout.addRow("Rating:", self.rating_filter)

        self.tuning_filter = QLineEdit()
        layout.addRow("Tuning:", self.tuning_filter)

        self.genre_filter = QLineEdit()
        layout.addRow("Genre:", self.genre_filter)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Reset | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.accept)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset_filters)
        layout.addRow(buttons)

    def reset_filters(self):
        self.band_filter.setCurrentIndex(0)
        self.album_filter.clear()
        self.rating_filter.setCurrentIndex(0)
        self.tuning_filter.clear()
        self.genre_filter.clear()

    def get_filter_data(self):
        return {
            "band":   self.band_filter.currentText() if self.band_filter.currentIndex() > 0 else "",
            "album":  self.album_filter.text().strip(),
            "rating": self.rating_filter.currentIndex(),
            "tuning": self.tuning_filter.text().strip(),
            "genre":  self.genre_filter.text().strip(),
        }


# ---------------------------------------------------------------------------
# Custom proxy model
# ---------------------------------------------------------------------------
class CustomProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_rating    = 0
        self.band_filter   = ""
        self.album_filter  = ""
        self.tuning_filter = ""
        self.genre_filter  = ""

    def set_rating_filter(self, min_rating):
        self.min_rating = min_rating
        self.invalidateFilter()

    def set_advanced_filters(self, filters):
        self.band_filter   = filters.get("band", "")
        self.album_filter  = filters.get("album", "")
        self.min_rating    = filters.get("rating", 0)
        self.tuning_filter = filters.get("tuning", "")
        self.genre_filter  = filters.get("genre", "")
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not super().filterAcceptsRow(source_row, source_parent):
            return False

        row = self.sourceModel()._data[source_row]

        if self.min_rating > 0:
            try:
                rating = int(row[5])
                if self.min_rating == 5:
                    if rating < 5: return False
                else:
                    if rating < self.min_rating: return False
            except (IndexError, ValueError):
                pass

        if self.band_filter   and self.band_filter.lower()   not in str(row[1]).lower(): return False
        if self.album_filter  and self.album_filter.lower()  not in str(row[2]).lower(): return False
        if self.tuning_filter and self.tuning_filter.lower() not in str(row[4]).lower(): return False
        if self.genre_filter  and self.genre_filter.lower()  not in str(row[6]).lower(): return False

        return True


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class GuitarTabApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guitar Tabs Collection Manager")
        self.setMinimumSize(1400, 800)
        self.drag_position = None

        # When frozen by PyInstaller, __file__ points into the temp _MEIPASS
        # folder which is deleted on exit. Use sys.executable so the database
        # is stored next to the .exe and persists between launches.
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path    = os.path.join(app_dir, "guitar_tabs.db")
        self.db_manager = DatabaseManager(self.db_path)

        try:
            self.db_manager.clean_up_empty_bands()
        except Exception as e:
            print(f"Warning: Could not clean up empty bands on startup: {e}")

        self.current_view = "all"
        self.initUI()
        self.load_data(preserve_tab=False)
        self.setupCustomTitleBar()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # ── Top bar ───────────────────────────────────────────────────
        top_controls = QHBoxLayout()
        mode_layout  = QHBoxLayout()

        self.all_tabs_btn = QPushButton("Tabs Collection")
        self.all_tabs_btn.setCheckable(True)
        self.all_tabs_btn.setChecked(True)
        self.all_tabs_btn.clicked.connect(lambda: self.switch_mode("all"))
        mode_layout.addWidget(self.all_tabs_btn)

        self.learned_tabs_btn = QPushButton("Learned")
        self.learned_tabs_btn.setCheckable(True)
        self.learned_tabs_btn.clicked.connect(lambda: self.switch_mode("learned"))
        mode_layout.addWidget(self.learned_tabs_btn)

        self.pitch_shifter_btn = QPushButton("Pitch Shifter")
        self.pitch_shifter_btn.clicked.connect(self.show_pitch_shifter)
        mode_layout.addWidget(self.pitch_shifter_btn)

        checked_style = """
QPushButton:checked {
    background-color: #e3ac63;
    border: none;
    color: black;
    font-weight: bold;
}
"""
        self.all_tabs_btn.setStyleSheet(checked_style)
        self.learned_tabs_btn.setStyleSheet(checked_style)
        self.pitch_shifter_btn.setStyleSheet(
            checked_style + "QPushButton:hover { background-color: #e3ac63; }"
        )

        top_controls.addLayout(mode_layout)
        top_controls.addStretch(1)

        # Action buttons (right side)
        action_layout = QHBoxLayout()
        for label, slot in [
            ("Add New Tab",  self.show_add_dialog),
            ("Add Multiple", self.show_batch_add_dialog),
            ("Import CSV",   self.import_from_csv),
            ("Export CSV",   self.export_to_csv),
            ("Export HTML",  self.export_to_html),      # ← NEW Round 2
            ("Backup DB",    self.backup_database),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            action_layout.addWidget(btn)

        top_controls.addLayout(action_layout)
        main_layout.addLayout(top_controls)
        main_layout.addSpacing(20)

        # ── Tab widget ────────────────────────────────────────────────
        self.tabs_widget = QTabWidget()
        self.tabs_widget.setTabPosition(QTabWidget.North)
        self.tabs_widget.setMovable(True)
        self.tabs_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs_widget)

        # ── Filter bar ────────────────────────────────────────────────
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))

        self.filter_field = QComboBox()
        self.filter_field.addItems(["All Fields", "Band", "Album", "Title", "Tuning", "Genre"])
        filter_layout.addWidget(self.filter_field)

        self.filter_text = QLineEdit()
        self.filter_text.setPlaceholderText("Type to filter...  [Ctrl+F]")
        self.filter_text.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_text)

        filter_layout.addWidget(QLabel("Rating:"))
        self.rating_filter = QComboBox()
        self.rating_filter.addItems(["Any", "1+", "2+", "3+", "4+", "5"])
        self.rating_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.rating_filter)

        self.adv_filter_btn = QPushButton("Advanced Filter")
        self.adv_filter_btn.clicked.connect(self.show_advanced_filter)
        filter_layout.addWidget(self.adv_filter_btn)

        main_layout.addLayout(filter_layout)
        self.statusBar().showMessage("Ready")

        # ── Keyboard shortcuts ────────────────────────────────────────
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self.delete_selected_tabs)
        QShortcut(QKeySequence(Qt.Key_F2),     self).activated.connect(self.edit_selected_tabs)
        QShortcut(QKeySequence("Ctrl+F"),      self).activated.connect(self.focus_filter)

    def focus_filter(self):
        self.filter_text.setFocus()
        self.filter_text.selectAll()

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------
    def switch_mode(self, mode):
        if mode == self.current_view:
            return
        self.current_view = mode
        self.all_tabs_btn.setChecked(mode == "all")
        self.learned_tabs_btn.setChecked(mode == "learned")
        self.load_data(preserve_tab=False)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data(self, preserve_tab=True):
        active_tab_name = None
        if preserve_tab and self.tabs_widget.count() > 0:
            active_tab_name = self.tabs_widget.tabText(self.tabs_widget.currentIndex())

        try:
            self.tabs_widget.clear()
            bands = self.db_manager.get_all_bands()

            if self.current_view == "all":
                self._load_all_tabs_view(bands)
            else:
                self._load_learned_tabs_view()

            if active_tab_name:
                for i in range(self.tabs_widget.count()):
                    if self.tabs_widget.tabText(i) == active_tab_name:
                        self.tabs_widget.setCurrentIndex(i)
                        break

            if self.current_view == "all":
                self.statusBar().showMessage(f"Loaded {len(bands)} bands")
            else:
                count = len(self.db_manager.get_all_learned_tabs())
                self.statusBar().showMessage(f"Loaded {count} learned tabs")

            self._setup_delegates()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")

    def _build_table_view(self, data, columns):
        table = QTableView()
        model = TabsDataModel(data, columns)
        proxy = CustomProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        table.setModel(proxy)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Notes column: interactive width so user can resize it
        try:
            notes_col = columns.index("Notes")
            header.setSectionResizeMode(notes_col, QHeaderView.Interactive)
            table.setColumnWidth(notes_col, 180)
        except ValueError:
            pass

        table.hideColumn(0)
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.ExtendedSelection)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)
        return table

    def _load_all_tabs_view(self, bands):
        # data: (id, band, album, title, tuning, rating, genre, notes)
        columns = [
            "ID", "Band", "Album", "Title", "Tuning",
            "Rating", "Genre", "Notes", "Ultimate Guitar"
        ]

        all_tabs = self.db_manager.get_all_tabs()
        if all_tabs:
            self.tabs_widget.addTab(self._build_table_view(all_tabs, columns), "All Tabs")

        general_tabs    = []
        bands_with_few  = set()

        for band_id, band_name in bands:
            band_tabs = self.db_manager.get_tabs_for_band(band_id)
            if len(band_tabs) < 5:
                general_tabs.extend(band_tabs)
                bands_with_few.add(band_name)
            elif band_tabs:
                self.tabs_widget.addTab(self._build_table_view(band_tabs, columns), band_name)

        if general_tabs:
            t = self._build_table_view(general_tabs, columns)
            t.setToolTip(f"Bands with fewer than 5 songs: {', '.join(sorted(bands_with_few))}")
            self.tabs_widget.insertTab(1, t, "General")

    def _load_learned_tabs_view(self):
        # data: (id, band, album, title, tuning, rating, genre, notes, learned_date)
        columns = [
            "ID", "Band", "Album", "Title", "Tuning",
            "Rating", "Genre", "Notes", "Learned Date", "Ultimate Guitar"
        ]
        learned_tabs = self.db_manager.get_all_learned_tabs()

        if not learned_tabs:
            empty = QWidget()
            lyt   = QVBoxLayout(empty)
            lbl   = QLabel(
                "No learned tabs yet.\n"
                "Right-click a tab in 'Tabs Collection' to mark it as learned."
            )
            lbl.setAlignment(Qt.AlignCenter)
            lyt.addWidget(lbl)
            self.tabs_widget.addTab(empty, "Learned")
            return

        self.tabs_widget.addTab(self._build_table_view(learned_tabs, columns), "All Learned")

        band_map       = {}
        general        = []
        bands_with_few = set()

        for tab in learned_tabs:
            band_map.setdefault(tab[1], []).append(tab)

        for band_name, tabs in band_map.items():
            if len(tabs) < 5:
                general.extend(tabs)
                bands_with_few.add(band_name)
            else:
                self.tabs_widget.addTab(self._build_table_view(tabs, columns), band_name)

        if general:
            t = self._build_table_view(general, columns)
            t.setToolTip(
                f"Bands with fewer than 5 learned songs: {', '.join(sorted(bands_with_few))}"
            )
            self.tabs_widget.insertTab(1, t, "General")

    # ------------------------------------------------------------------
    # Delegates setup  (UG button + inline star rating)
    # ------------------------------------------------------------------
    def _setup_delegates(self):
        # Store delegates as instance variables to prevent Python's GC from
        # collecting them. PyQt5 does NOT keep a Python-side reference for
        # setItemDelegateForColumn(), so local variables get freed and Qt
        # would access dangling C++ pointers → access violation / app crash.
        self._ug_delegate   = UltimateGuitarDelegate(self)
        self._star_delegate = StarRatingDelegate(self)

        for i in range(self.tabs_widget.count()):
            table = self.tabs_widget.widget(i)
            if not isinstance(table, QTableView):
                continue

            source_model = table.model().sourceModel()
            try:
                source_model.searchTabRequested.disconnect(self.searchTabOnline)
            except TypeError:
                pass
            source_model.searchTabRequested.connect(self.searchTabOnline)

            # Ultimate Guitar button column
            try:
                col = source_model.columns.index("Ultimate Guitar")
                table.setItemDelegateForColumn(col, self._ug_delegate)
                table.setColumnWidth(col, 100)
            except ValueError:
                pass

            # Inline star rating column
            try:
                col = source_model.columns.index("Rating")
                table.setItemDelegateForColumn(col, self._star_delegate)
            except ValueError:
                pass

    def searchTabOnline(self, band, title):
        try:
            encoded = urllib.parse.quote(f"{band} {title}")
            webbrowser.open(
                f"https://www.ultimate-guitar.com/search.php?search_type=title&value={encoded}"
            )
            self.statusBar().showMessage(f"Searching '{band} – {title}' on Ultimate Guitar…")
        except Exception as e:
            self.statusBar().showMessage(f"Error opening UG search: {e}")

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------
    def show_context_menu(self, position):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            index = current_tab.indexAt(position)
            sel   = current_tab.selectionModel()
            if not sel.hasSelection() and index.isValid():
                sel.select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

            selected_rows = sel.selectedRows()
            n = len(selected_rows)
            if n == 0:
                return

            menu = QMenu()

            if self.current_view == "all":
                learned_action = menu.addAction(
                    f"Mark {n} as Learned" if n > 1 else "Mark as Learned"
                )
            else:
                remove_action = menu.addAction(
                    f"Remove {n} from Learned" if n > 1 else "Remove from Learned"
                )

            menu.addSeparator()
            edit_action       = menu.addAction("Edit Tab" if n == 1 else f"Edit {n} Tabs (one at a time)")
            set_rating_action = menu.addAction(f"Set Rating for {n} Tabs" if n > 1 else "Set Rating")
            delete_action     = menu.addAction(f"Delete {n} Tab(s)" if n > 1 else "Delete Tab")

            action = menu.exec_(current_tab.viewport().mapToGlobal(position))
            if action is None:
                return

            if self.current_view == "all" and action == learned_action:
                self.add_tab_to_learned(current_tab)
            elif self.current_view == "learned" and action == remove_action:
                self.remove_from_learned(current_tab)
            elif action == edit_action:
                self.edit_selected_tabs()
            elif action == set_rating_action:
                self.bulk_set_rating()
            elif action == delete_action:
                self.delete_selected_tabs()

        except Exception as e:
            traceback.print_exc()
            self.statusBar().showMessage(f"Context menu error: {e}")

    # ------------------------------------------------------------------
    # Edit single tab  — FIXED Round 2: notes + learned date
    # ------------------------------------------------------------------
    def edit_selected_tabs(self):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            selected_rows = current_tab.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No tab selected.")
                return
            if len(selected_rows) > 1:
                QMessageBox.warning(self, "Edit", "Please select only one tab to edit at a time.")
                return

            proxy      = current_tab.model()
            source_row = proxy.mapToSource(selected_rows[0]).row()
            row_data   = proxy.sourceModel()._data[source_row]

            # All tabs:    (id, band, album, title, tuning, rating, genre, notes)
            # Learned tabs:(id, band, album, title, tuning, rating, genre, notes, learned_date)
            notes        = row_data[7] if len(row_data) > 7 else ""
            is_learned   = self.current_view == "learned"
            learned_date = row_data[8] if (is_learned and len(row_data) > 8) else None

            bands  = [b[1] for b in self.db_manager.get_all_bands()]
            dialog = AddTabDialog(
                bands, self,
                show_learned_date=is_learned,
                learned_date=learned_date
            )
            dialog.band_combo.setCurrentText(row_data[1])
            dialog.album.setText(row_data[2])
            dialog.title.setText(row_data[3])
            dialog.tuning.setCurrentText(row_data[4])
            dialog.rating_stars.setRating(int(row_data[5]))
            dialog.genre.setText(row_data[6])
            dialog.notes.setPlainText(notes)           # ← NEW: prefill notes

            if dialog.exec_() == QDialog.Accepted:
                updated = dialog.getTabData()
                if updated:
                    self.db_manager.update_tab(row_data[0], updated)

                    # ← NEW: save learned date if changed
                    if is_learned and "learned_date" in updated:
                        self.db_manager.update_learned_date(
                            row_data[0], updated["learned_date"]
                        )

                    self.load_data(preserve_tab=True)
                    self.statusBar().showMessage(
                        f"Updated: {updated['title']} by {updated['band']}"
                    )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to edit tab: {e}")

    # ------------------------------------------------------------------
    # Bulk Set Rating
    # ------------------------------------------------------------------
    def bulk_set_rating(self):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            selected_rows = current_tab.selectionModel().selectedRows()
            if not selected_rows:
                return

            dialog = SetRatingDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                return

            new_rating   = dialog.getRating()
            proxy        = current_tab.model()
            source_model = proxy.sourceModel()
            updated      = 0

            for proxy_index in selected_rows:
                source_row = proxy.mapToSource(proxy_index).row()
                tab_id     = source_model._data[source_row][0]
                try:
                    self.db_manager.update_rating(tab_id, new_rating)
                    updated += 1
                except Exception as e:
                    print(f"Error updating rating for tab {tab_id}: {e}")

            self.load_data(preserve_tab=True)
            stars = "★" * new_rating + "☆" * (5 - new_rating)
            self.statusBar().showMessage(f"Rating set to {stars} for {updated} tab(s)")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to set rating: {e}")

    # ------------------------------------------------------------------
    # Learned helpers
    # ------------------------------------------------------------------
    def add_tab_to_learned(self, table_view, index=None):
        sel     = table_view.selectionModel()
        indices = sel.selectedRows() or ([index] if (index and index.isValid()) else [])
        if not indices:
            return

        added = already = 0
        tab_title = ""

        for idx in indices:
            proxy        = table_view.model()
            source_model = proxy.sourceModel()
            source_row   = proxy.mapToSource(idx).row()
            if len(indices) == 1:
                tab_title = source_model._data[source_row][3]
            try:
                if self.db_manager.add_to_learned(source_model._data[source_row][0]):
                    added += 1
                else:
                    already += 1
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to mark as learned: {e}")

        msg = (
            (f"'{tab_title}' marked as learned" if added else f"'{tab_title}' already learned")
            if len(indices) == 1 else
            f"{added} marked as learned, {already} already learned"
        )
        self.statusBar().showMessage(msg)

        if self.current_view == "learned":
            self.load_data(preserve_tab=True)

    def remove_from_learned(self, table_view, index=None):
        indices = (
            [index] if (index and index.isValid())
            else table_view.selectionModel().selectedRows()
        )
        if not indices:
            return

        proxy        = table_view.model()
        source_model = proxy.sourceModel()
        removed      = 0
        last_title   = ""

        for idx in indices:
            source_row = proxy.mapToSource(idx).row()
            last_title = source_model._data[source_row][3]
            try:
                self.db_manager.remove_from_learned(source_model._data[source_row][0])
                removed += 1
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove from learned: {e}")

        self.load_data(preserve_tab=True)
        msg = (
            f"'{last_title}' removed from learned" if len(indices) == 1
            else f"{removed} tabs removed from learned"
        )
        self.statusBar().showMessage(msg)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_selected_tabs(self):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            selected_rows = current_tab.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No tabs selected.")
                return

            if QMessageBox.question(
                self, "Confirm Deletion",
                f"Delete {len(selected_rows)} selected tab(s)?",
                QMessageBox.Yes | QMessageBox.No
            ) != QMessageBox.Yes:
                return

            proxy        = current_tab.model()
            source_model = proxy.sourceModel()
            tab_ids      = []

            for pi in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                si = proxy.mapToSource(pi)
                if si.isValid() and 0 <= si.row() < len(source_model._data):
                    tab_ids.append(source_model._data[si.row()][0])

            deleted = 0
            for tab_id in tab_ids:
                try:
                    self.db_manager.delete_tab(tab_id)
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting tab {tab_id}: {e}")

            empty_bands = 0
            try:
                empty_bands = self.db_manager.clean_up_empty_bands() or 0
            except Exception as e:
                print(f"Error cleaning up bands: {e}")

            self.load_data(preserve_tab=True)
            msg = f"{deleted} tab(s) deleted"
            if empty_bands:
                msg += f", {empty_bands} empty band(s) removed"
            self.statusBar().showMessage(msg)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to delete tabs: {e}")

    # ------------------------------------------------------------------
    # Add dialogs
    # ------------------------------------------------------------------
    def show_add_dialog(self):
        bands  = [b[1] for b in self.db_manager.get_all_bands()]
        dialog = AddTabDialog(bands, self)

        if dialog.exec_() == QDialog.Accepted:
            tab_data = dialog.getTabData()
            if tab_data:
                try:
                    if self.db_manager.tab_exists(
                        tab_data["band"], tab_data["album"], tab_data["title"]
                    ):
                        QMessageBox.warning(
                            self, "Duplicate",
                            f"'{tab_data['title']}' by '{tab_data['band']}' already exists."
                        )
                        return
                    self.db_manager.add_tab(tab_data)
                    self.load_data(preserve_tab=True)
                    self.statusBar().showMessage(
                        f"Added: {tab_data['title']} by {tab_data['band']}"
                    )
                except ValueError as ve:
                    QMessageBox.warning(self, "Duplicate", str(ve))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tab: {e}")

    def show_batch_add_dialog(self):
        bands  = [b[1] for b in self.db_manager.get_all_bands()]
        dialog = BatchAddDialog(bands, self)

        if dialog.exec_() == QDialog.Accepted:
            try:
                tabs_data = dialog.getTabsData()
                success = duplicate = error = 0

                for tab in tabs_data:
                    try:
                        if self.db_manager.tab_exists(tab["band"], tab["album"], tab["title"]):
                            duplicate += 1
                            continue
                        self.db_manager.add_tab(tab)
                        success += 1
                    except ValueError:
                        duplicate += 1
                    except Exception as e:
                        error += 1
                        print(f"Error adding tab: {e}")

                self.load_data(preserve_tab=True)
                msg = f"Added {success} tab(s)"
                if duplicate: msg += f", {duplicate} duplicate(s) skipped"
                if error:     msg += f", {error} error(s)"
                self.statusBar().showMessage(msg)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add tabs: {e}")

    # ------------------------------------------------------------------
    # CSV Import
    # ------------------------------------------------------------------
    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            success = duplicate = error = 0

            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                print(f"CSV columns: {reader.fieldnames}")

                for row in reader:
                    try:
                        band  = row.get("band",  "").strip()
                        title = row.get("title", "").strip()
                        if not band or not title:
                            continue

                        album  = row.get("album", "").strip()
                        tuning = row.get("Tuning", row.get("tuning", "")).strip()
                        genre  = (row.get("genre") or row.get("genrge", "")).strip()
                        notes  = (row.get("notes") or row.get("Notes", "")).strip()

                        try:
                            rating = int(float(row.get("rating") or 1))
                        except (ValueError, TypeError):
                            rating = 1

                        if self.db_manager.tab_exists(band, album, title):
                            duplicate += 1
                            continue

                        self.db_manager.add_tab({
                            "band": band, "album": album, "title": title,
                            "tuning": tuning, "rating": rating,
                            "genre": genre, "notes": notes
                        })
                        success += 1

                    except ValueError:
                        duplicate += 1
                    except Exception as e:
                        print(f"Row error: {e}")
                        error += 1

            self.load_data(preserve_tab=True)
            msg = f"Imported {success} tab(s)"
            if duplicate: msg += f", {duplicate} duplicate(s) skipped"
            if error:     msg += f", {error} error(s)"
            self.statusBar().showMessage(msg)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to import CSV: {e}")

    # ------------------------------------------------------------------
    # Export CSV  — FIXED Round 2: includes Notes column
    # ------------------------------------------------------------------
    def export_to_csv(self):
        if self.current_view == "all":
            data         = self.db_manager.get_all_tabs()
            headers      = ["Band", "Album", "Title", "Tuning", "Rating", "Genre", "Notes"]
            default_name = "guitar_tabs_export.csv"
        else:
            data         = self.db_manager.get_all_learned_tabs()
            headers      = ["Band", "Album", "Title", "Tuning", "Rating", "Genre", "Notes", "Learned Date"]
            default_name = "guitar_tabs_learned_export.csv"

        if not data:
            QMessageBox.information(self, "Export", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default_name, "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in data:
                    writer.writerow(row[1:])  # skip ID

            self.statusBar().showMessage(
                f"Exported {len(data)} tab(s) to {os.path.basename(file_path)}"
            )
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Failed", f"Failed to export: {e}")

    # ------------------------------------------------------------------
    # Export HTML  ← NEW Round 2
    # ------------------------------------------------------------------
    def export_to_html(self):
        if self.current_view == "all":
            data         = self.db_manager.get_all_tabs()
            title        = "Guitar Tabs Collection"
            headers      = ["Band", "Album", "Title", "Tuning", "Rating", "Genre", "Notes"]
            default_name = "guitar_tabs_export.html"
        else:
            data         = self.db_manager.get_all_learned_tabs()
            title        = "Learned Guitar Tabs"
            headers      = ["Band", "Album", "Title", "Tuning", "Rating", "Genre", "Notes", "Learned Date"]
            default_name = "guitar_tabs_learned_export.html"

        if not data:
            QMessageBox.information(self, "Export", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML", default_name, "HTML Files (*.html);;All Files (*)"
        )
        if not file_path:
            return

        try:
            rows_html = ""
            for row in data:
                cols = row[1:]  # skip ID
                cells = ""
                for i, val in enumerate(cols):
                    # Rating column (index 4 in cols = index 5 in row)
                    if i == 4:
                        try:
                            r = int(val)
                        except (ValueError, TypeError):
                            r = 0
                        cells += f'<td class="rating">{"★" * r}{"☆" * (5 - r)}</td>'
                    else:
                        safe = str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if val else ""
                        cells += f"<td>{safe}</td>"
                rows_html += f"<tr>{cells}</tr>\n"

            header_cells = "".join(f"<th>{h}</th>" for h in headers)
            exported_at  = datetime.now().strftime("%Y-%m-%d %H:%M")

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body      {{ font-family: Arial, sans-serif; margin: 30px; color: #222; background: #fff; }}
    h1        {{ color: #e3ac63; border-bottom: 2px solid #e3ac63; padding-bottom: 6px; }}
    p.meta    {{ color: #666; font-size: 13px; margin-top: 0; }}
    table     {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th        {{ background: #3a3a3a; color: #e3ac63; padding: 9px 14px;
                 text-align: left; font-size: 13px; }}
    td        {{ padding: 7px 14px; border-bottom: 1px solid #e0e0e0;
                 font-size: 13px; vertical-align: top; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    tr:hover  {{ background: #fff8ec; }}
    .rating   {{ color: #FFD700; font-size: 15px; white-space: nowrap; }}
    @media print {{
      body {{ margin: 10px; }}
      tr:hover {{ background: none; }}
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p class="meta">Exported: {exported_at} &nbsp;|&nbsp; {len(data)} tab(s)</p>
  <table>
    <thead><tr>{header_cells}</tr></thead>
    <tbody>
{rows_html}    </tbody>
  </table>
</body>
</html>"""

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)

            self.statusBar().showMessage(
                f"✓ Exported {len(data)} tab(s) → {os.path.basename(file_path)}"
            )
            # Open in browser immediately
            webbrowser.open(f"file:///{os.path.abspath(file_path)}")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Failed", f"Failed to export HTML: {e}")

    # ------------------------------------------------------------------
    # Database Backup
    # ------------------------------------------------------------------
    def backup_database(self):
        try:
            timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"guitar_tabs_backup_{timestamp}.db"
            backup_path = os.path.join(os.path.dirname(self.db_path), backup_name)
            shutil.copy2(self.db_path, backup_path)
            self.statusBar().showMessage(f"✓ Backup saved: {backup_name}")
            QMessageBox.information(
                self, "Backup Successful",
                f"Database backed up to:\n{backup_path}"
            )
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Backup Failed", f"Failed to backup database:\n{e}")

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------
    def apply_filter(self):
        if self.tabs_widget.count() == 0:
            return
        current_tab = self.tabs_widget.currentWidget()
        if not isinstance(current_tab, QTableView):
            return
        proxy = current_tab.model()
        if not isinstance(proxy, CustomProxyModel):
            return

        field_map = {
            "All Fields": -1, "Band": 1, "Album": 2,
            "Title": 3, "Tuning": 4, "Genre": 6,
        }
        proxy.setFilterKeyColumn(field_map.get(self.filter_field.currentText(), -1))
        proxy.set_rating_filter(self.rating_filter.currentIndex())
        proxy.setFilterFixedString(self.filter_text.text())

    def show_advanced_filter(self):
        bands  = [b[1] for b in self.db_manager.get_all_bands()]
        dialog = AdvancedFilterDialog(bands, self)
        if dialog.exec_() == QDialog.Accepted:
            current_tab = self.tabs_widget.currentWidget()
            if isinstance(current_tab, QTableView):
                proxy = current_tab.model()
                if isinstance(proxy, CustomProxyModel):
                    proxy.set_advanced_filters(dialog.get_filter_data())
                    self.statusBar().showMessage("Advanced filter applied")

    # ------------------------------------------------------------------
    # Tab changed
    # ------------------------------------------------------------------
    def on_tab_changed(self, index):
        if index < 0:
            return
        tab_name = self.tabs_widget.tabText(index)
        count    = 0
        widget   = self.tabs_widget.widget(index)
        if isinstance(widget, QTableView) and isinstance(widget.model(), QSortFilterProxyModel):
            count = widget.model().rowCount()
        self.statusBar().showMessage(f"{tab_name}: {count} tab(s)")

    # ------------------------------------------------------------------
    # Pitch Shifter
    # ------------------------------------------------------------------
    def show_pitch_shifter(self):
        PitchShifterDialog(self.db_manager, self).exec_()

    # ------------------------------------------------------------------
    # Custom title bar
    # ------------------------------------------------------------------
    def setupCustomTitleBar(self):
        self.setWindowFlags(Qt.FramelessWindowHint)

        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: #3a3a3a;")

        lyt = QHBoxLayout(title_bar)
        lyt.setContentsMargins(10, 0, 10, 0)
        lyt.setSpacing(5)

        title_label = QLabel("Guitar Tabs Collection Manager")
        title_label.setStyleSheet("color: white; font-weight: bold;")
        lyt.addWidget(title_label)
        lyt.addStretch()

        btn_style = """
QPushButton {
    background-color: transparent;
    color: white;
    border: none;
    font-size: 16px;
    font-family: Arial;
    padding: 0;
    margin: 0;
}
QPushButton:hover { background-color: #555555; }
"""
        min_btn = QPushButton("_")
        min_btn.setFixedSize(30, 30)
        min_btn.setStyleSheet(btn_style)
        min_btn.clicked.connect(self.showMinimized)

        max_btn = QPushButton("□")
        max_btn.setFixedSize(30, 30)
        max_btn.setStyleSheet(btn_style)
        max_btn.clicked.connect(self.toggleMaximized)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(btn_style + "QPushButton:hover { background-color: #E81123; }")
        close_btn.clicked.connect(self.close)

        for b in (min_btn, max_btn, close_btn):
            lyt.addWidget(b)

        self.centralWidget().layout().insertWidget(0, title_bar)

        title_bar.mousePressEvent   = self._tb_mouse_press
        title_bar.mouseMoveEvent    = self._tb_mouse_move
        title_bar.mouseReleaseEvent = self._tb_mouse_release

    def toggleMaximized(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _tb_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()

    def _tb_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)

    def _tb_mouse_release(self, event):
        self.drag_position = None
