import os
import csv
import webbrowser
import urllib.parse
import traceback

from PyQt5.QtWidgets import (
    QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QComboBox, QLabel, QLineEdit, QHeaderView, QTabWidget,
    QMessageBox, QFileDialog, QDialog, QFormLayout, QDialogButtonBox,
    QMenu, QAction, QSizePolicy, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QItemSelectionModel, QEvent
from PyQt5.QtGui import QColor

from tabs_data_model import TabsDataModel
from database_manager import DatabaseManager
from add_tab_dialog import AddTabDialog
from add_tab_multi import BatchAddDialog
from pitch_shifter import PitchShifterDialog


# ---------------------------------------------------------------------------
# Module-level delegate — defined once, reused on every load_data() call
# ---------------------------------------------------------------------------
class UltimateGuitarDelegate(QStyledItemDelegate):
    """Renders a clickable 'Open' button in the Ultimate Guitar column."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window

    def paint(self, painter, option, index):
        painter.save()
        bg = QColor("#eaa13f") if option.state & 0x2000 else QColor("#e3ac63")  # State_MouseOver
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
            band = source_model._data[source_row][1]
            title = source_model._data[source_row][3]
            self._main_window.searchTabOnline(band, title)
            return True
        return super().editorEvent(event, model, option, index)


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
            "band": self.band_filter.currentText() if self.band_filter.currentIndex() > 0 else "",
            "album": self.album_filter.text().strip(),
            "rating": self.rating_filter.currentIndex(),
            "tuning": self.tuning_filter.text().strip(),
            "genre": self.genre_filter.text().strip(),
        }


# ---------------------------------------------------------------------------
# Custom proxy model
# ---------------------------------------------------------------------------
class CustomProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_rating = 0
        self.band_filter = ""
        self.album_filter = ""
        self.tuning_filter = ""
        self.genre_filter = ""

    def set_rating_filter(self, min_rating):
        self.min_rating = min_rating
        self.invalidateFilter()

    def set_advanced_filters(self, filters):
        self.band_filter = filters.get("band", "")
        self.album_filter = filters.get("album", "")
        self.min_rating = filters.get("rating", 0)
        self.tuning_filter = filters.get("tuning", "")
        self.genre_filter = filters.get("genre", "")
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not super().filterAcceptsRow(source_row, source_parent):
            return False

        m = self.sourceModel()
        row = m._data[source_row]

        # Rating — column 5 in both 'all' and 'learned' data tuples
        if self.min_rating > 0:
            try:
                rating = int(row[5])
                if self.min_rating == 5:
                    if rating < 5:
                        return False
                else:
                    if rating < self.min_rating:
                        return False
            except (IndexError, ValueError):
                pass

        if self.band_filter and self.band_filter.lower() not in str(row[1]).lower():
            return False
        if self.album_filter and self.album_filter.lower() not in str(row[2]).lower():
            return False
        if self.tuning_filter and self.tuning_filter.lower() not in str(row[4]).lower():
            return False
        if self.genre_filter and self.genre_filter.lower() not in str(row[6]).lower():
            return False

        return True


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class GuitarTabsApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guitar Tabs Collection Manager")
        self.setMinimumSize(1400, 800)

        self.drag_position = None

        app_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(app_dir, "guitar_tabs.db")
        self.db_manager = DatabaseManager(db_path)

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

        # ── Top controls ──────────────────────────────────────────────
        top_controls = QHBoxLayout()

        mode_buttons_layout = QHBoxLayout()

        self.all_tabs_btn = QPushButton("Tabs Collection")
        self.all_tabs_btn.setCheckable(True)
        self.all_tabs_btn.setChecked(True)
        self.all_tabs_btn.clicked.connect(lambda: self.switch_mode("all"))
        mode_buttons_layout.addWidget(self.all_tabs_btn)

        self.learned_tabs_btn = QPushButton("Learned")
        self.learned_tabs_btn.setCheckable(True)
        self.learned_tabs_btn.clicked.connect(lambda: self.switch_mode("learned"))
        mode_buttons_layout.addWidget(self.learned_tabs_btn)

        self.pitch_shifter_btn = QPushButton("Pitch Shifter")
        self.pitch_shifter_btn.setCheckable(False)
        self.pitch_shifter_btn.clicked.connect(self.show_pitch_shifter)
        mode_buttons_layout.addWidget(self.pitch_shifter_btn)

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
        self.pitch_shifter_btn.setStyleSheet(checked_style + """
QPushButton:hover { background-color: #e3ac63; }
""")

        top_controls.addLayout(mode_buttons_layout)
        top_controls.addStretch(1)

        action_buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add New Tab")
        self.add_btn.clicked.connect(self.show_add_dialog)
        self.add_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        action_buttons_layout.addWidget(self.add_btn)

        self.batch_add_btn = QPushButton("Add Multiple")
        self.batch_add_btn.clicked.connect(self.show_batch_add_dialog)
        self.batch_add_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        action_buttons_layout.addWidget(self.batch_add_btn)

        self.csv_import_btn = QPushButton("Import CSV")
        self.csv_import_btn.clicked.connect(self.import_from_csv)
        self.csv_import_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        action_buttons_layout.addWidget(self.csv_import_btn)

        top_controls.addLayout(action_buttons_layout)
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
        self.filter_text.setPlaceholderText("Type to filter...")
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

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------
    def switch_mode(self, mode):
        if mode == self.current_view:
            return
        self.current_view = mode
        if mode == "all":
            self.all_tabs_btn.setChecked(True)
            self.learned_tabs_btn.setChecked(False)
        else:
            self.all_tabs_btn.setChecked(False)
            self.learned_tabs_btn.setChecked(True)
        # When switching modes we always want to land on the first tab
        self.load_data(preserve_tab=False)

    # ------------------------------------------------------------------
    # Data loading  ← FIX: preserve_tab saves & restores active tab
    # ------------------------------------------------------------------
    def load_data(self, preserve_tab=True):
        """Reload data from the database.

        Args:
            preserve_tab: When True (default) the currently active band tab
                          is remembered by name and re-selected after rebuild,
                          so editing/deleting never jumps back to the first tab.
                          Pass False when intentionally resetting (mode switch,
                          initial load).
        """
        # ── Remember active tab name before clearing ──────────────────
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

            # ── Restore active tab by name ────────────────────────────
            if active_tab_name:
                for i in range(self.tabs_widget.count()):
                    if self.tabs_widget.tabText(i) == active_tab_name:
                        self.tabs_widget.setCurrentIndex(i)
                        break

            # Status bar
            if self.current_view == "all":
                self.statusBar().showMessage(f"Loaded {len(bands)} bands")
            else:
                learned_count = len(self.db_manager.get_all_learned_tabs())
                self.statusBar().showMessage(f"Loaded {learned_count} learned tabs")

            self._setup_ug_delegates()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")
            self.statusBar().showMessage("Error loading data")

    def _build_table_view(self, data, columns):
        """Helper: create a fully-configured QTableView for the given data."""
        table = QTableView()
        model = TabsDataModel(data, columns)
        proxy = CustomProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        table.setModel(proxy)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.hideColumn(0)
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.ExtendedSelection)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)
        return table

    def _load_all_tabs_view(self, bands):
        columns = ["ID", "Band", "Album", "Title", "Tuning", "Rating", "Genre", "Ultimate Guitar"]
        all_tabs = self.db_manager.get_all_tabs()
        if all_tabs:
            self.tabs_widget.addTab(self._build_table_view(all_tabs, columns), "All Tabs")

        general_tabs = []
        bands_with_few = set()

        for band_id, band_name in bands:
            band_tabs = self.db_manager.get_tabs_for_band(band_id)
            if len(band_tabs) < 5:
                general_tabs.extend(band_tabs)
                bands_with_few.add(band_name)
            elif band_tabs:
                self.tabs_widget.addTab(self._build_table_view(band_tabs, columns), band_name)

        if general_tabs:
            general_table = self._build_table_view(general_tabs, columns)
            general_table.setToolTip(
                f"Bands with fewer than 5 songs: {', '.join(sorted(bands_with_few))}"
            )
            self.tabs_widget.insertTab(1, general_table, "General")

    def _load_learned_tabs_view(self):
        columns = ["ID", "Band", "Album", "Title", "Tuning", "Rating", "Genre", "Learned Date", "Ultimate Guitar"]
        learned_tabs = self.db_manager.get_all_learned_tabs()

        if not learned_tabs:
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_label = QLabel(
                "No learned tabs yet.\n"
                "Right-click on any tab in 'Tabs Collection' to mark it as learned."
            )
            empty_label.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(empty_label)
            self.tabs_widget.addTab(empty_widget, "Learned")
            return

        self.tabs_widget.addTab(self._build_table_view(learned_tabs, columns), "All Learned")

        band_learned_tabs = {}
        for tab in learned_tabs:
            band_learned_tabs.setdefault(tab[1], []).append(tab)

        general_learned = []
        bands_with_few = set()

        for band_name, tabs in band_learned_tabs.items():
            if len(tabs) < 5:
                general_learned.extend(tabs)
                bands_with_few.add(band_name)
            else:
                self.tabs_widget.addTab(self._build_table_view(tabs, columns), band_name)

        if general_learned:
            general_table = self._build_table_view(general_learned, columns)
            general_table.setToolTip(
                f"Bands with fewer than 5 learned songs: {', '.join(sorted(bands_with_few))}"
            )
            self.tabs_widget.insertTab(1, general_table, "General")

    # ------------------------------------------------------------------
    # Ultimate Guitar button delegates
    # ------------------------------------------------------------------
    def _setup_ug_delegates(self):
        delegate = UltimateGuitarDelegate(self)
        for i in range(self.tabs_widget.count()):
            table = self.tabs_widget.widget(i)
            if not isinstance(table, QTableView):
                continue
            source_model = table.model().sourceModel()
            # Connect signal (guard against duplicate connections)
            try:
                source_model.searchTabRequested.disconnect(self.searchTabOnline)
            except TypeError:
                pass
            source_model.searchTabRequested.connect(self.searchTabOnline)
            try:
                ug_col = source_model.columns.index("Ultimate Guitar")
                table.setItemDelegateForColumn(ug_col, delegate)
                table.setColumnWidth(ug_col, 100)
            except ValueError:
                pass

    def searchTabOnline(self, band, title):
        try:
            encoded = urllib.parse.quote(f"{band} {title}")
            url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={encoded}"
            webbrowser.open(url)
            self.statusBar().showMessage(f"Searching '{band} – {title}' on Ultimate Guitar…")
        except Exception as e:
            traceback.print_exc()
            self.statusBar().showMessage(f"Error opening UG search: {e}")

    # ------------------------------------------------------------------
    # Context menu  (single handler for both views)
    # ------------------------------------------------------------------
    def show_context_menu(self, position):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            index = current_tab.indexAt(position)
            selection_model = current_tab.selectionModel()

            if not selection_model.hasSelection() and index.isValid():
                selection_model.select(
                    index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
                )

            selected_rows = selection_model.selectedRows()
            if not selected_rows:
                return

            n = len(selected_rows)
            menu = QMenu()

            if self.current_view == "all":
                learned_action = menu.addAction(f"Mark {n} as Learned" if n > 1 else "Mark as Learned")
            else:
                remove_action = menu.addAction(f"Remove {n} from Learned" if n > 1 else "Remove from Learned")

            edit_action = menu.addAction(f"Edit {n} Tab(s)" if n > 1 else "Edit Tab")
            delete_action = menu.addAction(f"Delete {n} Tab(s)" if n > 1 else "Delete Tab")

            action = menu.exec_(current_tab.viewport().mapToGlobal(position))
            if action is None:
                return

            if self.current_view == "all" and action == learned_action:
                self.add_tab_to_learned(current_tab)
            elif self.current_view == "learned" and action == remove_action:
                self.remove_from_learned(current_tab)
            elif action == edit_action:
                self.edit_selected_tabs()
            elif action == delete_action:
                self.delete_selected_tabs()

        except Exception as e:
            traceback.print_exc()
            self.statusBar().showMessage(f"Context menu error: {e}")

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------
    def edit_selected_tabs(self):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            selected_rows = current_tab.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No tabs selected.")
                return
            if len(selected_rows) > 1:
                QMessageBox.warning(self, "Edit Tabs", "Please edit tabs one at a time.")
                return

            proxy_model = current_tab.model()
            source_model = proxy_model.sourceModel()
            source_row = proxy_model.mapToSource(selected_rows[0]).row()
            row_data = source_model._data[source_row]

            tab = {
                'id':     row_data[0],
                'band':   row_data[1],
                'album':  row_data[2],
                'title':  row_data[3],
                'tuning': row_data[4],
                'rating': int(row_data[5]),
                'genre':  row_data[6],
            }

            bands = [b[1] for b in self.db_manager.get_all_bands()]
            dialog = AddTabDialog(bands, self)
            dialog.band_combo.setCurrentText(tab['band'])
            dialog.album.setText(tab['album'])
            dialog.title.setText(tab['title'])
            dialog.tuning.setCurrentText(tab['tuning'])
            dialog.rating_stars.setRating(tab['rating'])
            dialog.genre.setText(tab['genre'])

            if dialog.exec_() == QDialog.Accepted:
                updated = dialog.getTabData()
                if updated:
                    self.db_manager.update_tab(tab['id'], updated)
                    # preserve_tab=True keeps us on the current band tab
                    self.load_data(preserve_tab=True)
                    self.statusBar().showMessage(
                        f"Updated: {updated['title']} by {updated['band']}"
                    )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to edit tab: {e}")

    # ------------------------------------------------------------------
    # Learned helpers
    # ------------------------------------------------------------------
    def add_tab_to_learned(self, table_view, index=None):
        selection_model = table_view.selectionModel()
        indices = selection_model.selectedRows()
        if not indices:
            if index and index.isValid():
                indices = [index]
            else:
                return

        added = 0
        already = 0
        tab_title = ""

        for idx in indices:
            proxy_model = table_view.model()
            source_model = proxy_model.sourceModel()
            source_row = proxy_model.mapToSource(idx).row()
            if len(indices) == 1:
                tab_title = source_model._data[source_row][3]
            tab_id = source_model._data[source_row][0]
            try:
                if self.db_manager.add_to_learned(tab_id):
                    added += 1
                else:
                    already += 1
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to mark tab as learned: {e}")

        if len(indices) == 1:
            msg = f"'{tab_title}' marked as learned" if added else f"'{tab_title}' already marked as learned"
        else:
            msg = f"{added} tabs marked as learned, {already} already learned"
        self.statusBar().showMessage(msg)

        if self.current_view == "learned":
            self.load_data(preserve_tab=True)

    def remove_from_learned(self, table_view, index=None):
        indices = [index] if (index and index.isValid()) else table_view.selectionModel().selectedRows()
        if not indices:
            return

        proxy_model = table_view.model()
        source_model = proxy_model.sourceModel()
        removed = 0
        last_title = ""

        for idx in indices:
            source_row = proxy_model.mapToSource(idx).row()
            last_title = source_model._data[source_row][3]
            tab_id = source_model._data[source_row][0]
            try:
                self.db_manager.remove_from_learned(tab_id)
                removed += 1
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove from learned: {e}")

        self.load_data(preserve_tab=True)

        msg = (f"'{last_title}' removed from learned" if len(indices) == 1
               else f"{removed} tabs removed from learned")
        self.statusBar().showMessage(msg)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_selected_tabs(self):
        try:
            current_tab = self.tabs_widget.currentWidget()
            if not isinstance(current_tab, QTableView):
                return

            selection_model = current_tab.selectionModel()
            selected_rows = selection_model.selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No tabs selected.")
                return

            if QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Delete {len(selected_rows)} selected tab(s)?",
                QMessageBox.Yes | QMessageBox.No,
            ) != QMessageBox.Yes:
                return

            proxy_model = current_tab.model()
            source_model = proxy_model.sourceModel()

            tab_ids = []
            for proxy_index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                source_index = proxy_model.mapToSource(proxy_index)
                if not source_index.isValid():
                    continue
                source_row = source_index.row()
                if 0 <= source_row < len(source_model._data):
                    tab_ids.append(source_model._data[source_row][0])

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
        bands = [b[1] for b in self.db_manager.get_all_bands()]
        dialog = AddTabDialog(bands, self)

        if dialog.exec_() == QDialog.Accepted:
            tab_data = dialog.getTabData()
            if tab_data:
                try:
                    if self.db_manager.tab_exists(tab_data["band"], tab_data["album"], tab_data["title"]):
                        QMessageBox.warning(
                            self, "Duplicate Tab",
                            f"'{tab_data['title']}' by '{tab_data['band']}' "
                            f"(album: '{tab_data['album']}') already exists."
                        )
                        return
                    self.db_manager.add_tab(tab_data)
                    self.load_data(preserve_tab=True)
                    self.statusBar().showMessage(
                        f"Added: {tab_data['title']} by {tab_data['band']}"
                    )
                except ValueError as ve:
                    QMessageBox.warning(self, "Duplicate Tab", str(ve))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tab: {e}")

    def show_batch_add_dialog(self):
        bands = [b[1] for b in self.db_manager.get_all_bands()]
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
                        print(f"Error adding tab {tab.get('title', '?')}: {e}")

                self.load_data(preserve_tab=True)
                msg = f"Added {success} tab(s)"
                if duplicate:
                    msg += f", {duplicate} duplicate(s) skipped"
                if error:
                    msg += f", {error} error(s)"
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
                        band = row.get("band", "").strip()
                        title = row.get("title", "").strip()
                        if not band or not title:
                            continue

                        album = row.get("album", "").strip()
                        tuning = row.get("Tuning", row.get("tuning", "")).strip()
                        genre = (row.get("genre") or row.get("genrge", "")).strip()

                        try:
                            rating = int(float(row.get("rating") or 1))
                        except (ValueError, TypeError):
                            rating = 1

                        if self.db_manager.tab_exists(band, album, title):
                            duplicate += 1
                            continue

                        self.db_manager.add_tab(
                            {"band": band, "album": album, "title": title,
                             "tuning": tuning, "rating": rating, "genre": genre}
                        )
                        success += 1

                    except ValueError:
                        duplicate += 1
                    except Exception as e:
                        print(f"Row error: {e}")
                        error += 1

            self.load_data(preserve_tab=True)
            msg = f"Imported {success} tab(s)"
            if duplicate:
                msg += f", {duplicate} duplicate(s) skipped"
            if error:
                msg += f", {error} error(s)"
            self.statusBar().showMessage(msg)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to import CSV: {e}")

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
        bands = [b[1] for b in self.db_manager.get_all_bands()]
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
        count = 0
        widget = self.tabs_widget.widget(index)
        if isinstance(widget, QTableView) and isinstance(widget.model(), QSortFilterProxyModel):
            count = widget.model().rowCount()
        self.statusBar().showMessage(f"{tab_name}: {count} tab(s)")

    # ------------------------------------------------------------------
    # Pitch Shifter
    # ------------------------------------------------------------------
    def show_pitch_shifter(self):
        dialog = PitchShifterDialog(self.db_manager, self)
        dialog.exec_()

    # ------------------------------------------------------------------
    # Custom title bar  (drag logic lives here, NOT on main window)
    # ------------------------------------------------------------------
    def setupCustomTitleBar(self):
        self.setWindowFlags(Qt.FramelessWindowHint)

        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: #3a3a3a;")

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(5)

        title_label = QLabel("Guitar Tabs Collection Manager")
        title_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(title_label)
        layout.addStretch()

        btn_style = """
QPushButton {
    background-color: transparent; color: white; border: none;
    font-size: 16px; font-family: Arial; padding: 0; margin: 0;
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

        layout.addWidget(min_btn)
        layout.addWidget(max_btn)
        layout.addWidget(close_btn)

        self.centralWidget().layout().insertWidget(0, title_bar)

        # Title bar drag — only the title bar moves the window
        title_bar.mousePressEvent = self._tb_mouse_press
        title_bar.mouseMoveEvent = self._tb_mouse_move
        title_bar.mouseReleaseEvent = self._tb_mouse_release

    def toggleMaximized(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _tb_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _tb_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def _tb_mouse_release(self, event):
        self.drag_position = None
        event.accept()
