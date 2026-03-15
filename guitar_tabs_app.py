import os
import sys
import re
import csv
import io
import json
import zipfile
import shutil
import traceback
import webbrowser
import urllib.parse
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QComboBox, QLabel, QLineEdit, QHeaderView, QTabWidget,
    QMessageBox, QFileDialog, QDialog, QFormLayout, QDialogButtonBox,
    QMenu, QStyledItemDelegate, QShortcut,
    QSpinBox, QTableWidget, QTableWidgetItem, QProgressBar, QAbstractItemView, QFrame
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QItemSelectionModel, QEvent, QPoint, QTimer, QRect, QRectF
from PyQt5.QtGui import QColor, QKeySequence, QFont, QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from title_checker import TitleChecker

def _resource_path(relative):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)

def _load_icon_white(relative, size=28):
    """Load a PNG or SVG icon recoloured white on transparent — no pixel loops."""
    path = _resource_path(relative)
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    if relative.lower().endswith('.svg'):
        # Recolour SVG in-memory: dark fills → white, light fills → none (transparent)
        with open(path, 'r', encoding='utf-8') as f:
            svg = f.read()
        def _replace_fill(m):
            color = m.group(1).lower().strip()
            if color in ('none', 'transparent', 'currentcolor'):
                return m.group(0)
            try:
                c = color.lstrip('#')
                if len(c) == 3:
                    c = ''.join(x * 2 for x in c)
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                return 'fill="white"' if (r + g + b) // 3 < 128 else 'fill="none"'
            except Exception:
                return m.group(0)
        svg = re.sub(r'fill="([^"]+)"', _replace_fill, svg)
        QSvgRenderer(bytearray(svg.encode('utf-8'))).render(painter)
    else:
        src = QPixmap(path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(0, 0, src)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(px.rect(), QColor(255, 255, 255))
    painter.end()
    return QIcon(px)


from tabs_data_model import TabsDataModel
from database_manager import DatabaseManager
from add_tab_dialog import AddTabDialog, StarRating
from add_tab_multi import BatchAddDialog
from pitch_shifter import PitchShifterDialog


# ---------------------------------------------------------------------------
# "Open with" column delegate — UG + Spotify icon buttons
# ---------------------------------------------------------------------------
_ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images", "Icons")

def _load_svg_renderer(filename):
    path = os.path.join(_ICON_DIR, filename)
    return QSvgRenderer(path) if os.path.exists(path) else None


def _svg_to_icon(filename, size=18):
    """Render an SVG from _ICON_DIR to a QIcon of the given pixel size."""
    path = os.path.join(_ICON_DIR, filename)
    if not os.path.exists(path):
        return QIcon()
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    QSvgRenderer(path).render(p, QRectF(0, 0, size, size))
    p.end()
    return QIcon(px)


class OpenWithDelegate(QStyledItemDelegate):
    """Draws two icon buttons (Ultimate Guitar | Spotify) inside a single cell."""

    _UG_BG      = QColor("#e3ac63")
    _UG_HOVER   = QColor("#eaa13f")
    _SP_BG      = QColor("#1db954")
    _SP_HOVER   = QColor("#1ed760")

    # SVG renderers are shared across all instances (loaded once)
    _ug_svg      = None
    _spotify_svg = None

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        if OpenWithDelegate._ug_svg is None:
            OpenWithDelegate._ug_svg      = _load_svg_renderer("ultimate-guitar.svg")
            OpenWithDelegate._spotify_svg = _load_svg_renderer("spotify-svgrepo-com.svg")

    # ------------------------------------------------------------------
    def _button_rects(self, cell_rect):
        r   = cell_rect.adjusted(2, 2, -2, -2)
        mid = r.left() + r.width() // 2 - 1
        ug_r = QRect(r.left(), r.top(), mid - r.left(),      r.height())
        sp_r = QRect(mid + 2,  r.top(), r.right() - mid - 2, r.height())
        return ug_r, sp_r

    def paint(self, painter, option, _index):
        painter.save()
        ug_r, sp_r = self._button_rects(option.rect)

        # UG button
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._UG_BG)
        painter.drawRoundedRect(ug_r, 4, 4)
        if self._ug_svg:
            self._ug_svg.render(painter, QRectF(ug_r.adjusted(3, 3, -3, -3)))

        # Spotify button
        painter.setBrush(self._SP_BG)
        painter.drawRoundedRect(sp_r, 4, 4)
        if self._spotify_svg:
            self._spotify_svg.render(painter, QRectF(sp_r.adjusted(3, 3, -3, -3)))

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            ug_r, sp_r = self._button_rects(option.rect)
            source_model = model.sourceModel()
            source_row   = model.mapToSource(index).row()
            band  = source_model.get_row(source_row)[1]
            title = source_model.get_row(source_row)[3]
            if ug_r.contains(event.pos()):
                self._mw.searchTabOnline(band, title)
                return True
            if sp_r.contains(event.pos()):
                self._mw.searchOnSpotify(band, title)
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
            rating = int(source_model.get_row(source_row)[5])
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
            tab_id       = source_model.get_row(source_row)[0]

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
        self.band_filter.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.band_filter.setMaxVisibleItems(15)
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

        row = self.sourceModel().get_row(source_row)

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

    def lessThan(self, left, right):
        src = self.sourceModel()
        sort_col = self.sortColumn()

        def cell(row, col):
            return (src.data(src.index(row, col), Qt.DisplayRole) or "").lower()

        # Primary: whichever column the header was clicked
        lv, rv = cell(left.row(), sort_col), cell(right.row(), sort_col)
        if lv != rv:
            return lv < rv

        # Tiebreakers: Band → Album → Title
        for col in (1, 2, 3):
            if col == sort_col:
                continue
            lv, rv = cell(left.row(), col), cell(right.row(), col)
            if lv != rv:
                return lv < rv

        return False


# ---------------------------------------------------------------------------
# Bulk Checker Dialog
# ---------------------------------------------------------------------------
class BulkCheckerDialog(QDialog):
    def __init__(self, db_manager, title_checker, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.checker    = title_checker
        self.setWindowTitle("Bulk Tab Checker")
        self.setMinimumSize(920, 580)
        self._pending = []
        self._active  = 0
        self._total   = 0

        layout = QVBoxLayout(self)

        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        self._status = QLabel("Loading…")
        layout.addWidget(self._status)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["", "Band", "Current Title", "Suggested Title", "Current Album", "Suggested Album"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 32)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._apply_btn = QPushButton("Apply Selected")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._apply_selected)
        btn_row.addStretch()
        btn_row.addWidget(self._apply_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        QTimer.singleShot(0, self._start)

    def _start(self):
        tabs = self.db_manager.get_all_tabs()
        self._total = len(tabs)
        self._progress.setRange(0, self._total)
        self._progress.setValue(0)
        self._status.setText(f"Checking {self._total} tabs…")
        # get_all_tabs returns: id, band, album, title, tuning, rating, genre, notes
        for row in tabs:
            tab_id, band, album, title = row[0], row[1], row[2], row[3]
            self._pending.append((band, title, tab_id, album))
        self._fill_workers()

    def _fill_workers(self):
        # MusicBrainz enforces 1 req/sec — run only one worker at a time
        while self._active < 1 and self._pending:
            band, title, tab_id, album = self._pending.pop(0)
            self._active += 1
            self.checker.check(
                band, title, tab_id, "full",
                lambda b, t, tid, d, al=album: self._on_result(b, t, tid, d, al)
            )

    def _on_result(self, band, title, tab_id, data, current_album):
        self._active -= 1
        done = self._total - len(self._pending) - self._active
        self._progress.setValue(done)

        sug_title = data.get('title', '')
        sug_band  = data.get('band',  band)
        sug_album = data.get('album', '')

        title_diff = sug_title and sug_title.lower() != title.lower()
        album_diff = (sug_album and
                      sug_album.lower() != (current_album or '').lower())

        if title_diff or album_diff:
            r = self._table.rowCount()
            self._table.insertRow(r)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            high_conf = bool(sug_title and title.lower() in sug_title.lower())
            chk.setCheckState(Qt.Checked if high_conf else Qt.Unchecked)
            self._table.setItem(r, 0, chk)

            band_item = QTableWidgetItem(sug_band)
            band_item.setData(Qt.UserRole, tab_id)
            self._table.setItem(r, 1, band_item)
            self._table.setItem(r, 2, QTableWidgetItem(title))
            self._table.setItem(r, 3, QTableWidgetItem(sug_title or title))
            self._table.setItem(r, 4, QTableWidgetItem(current_album or ''))
            self._table.setItem(r, 5, QTableWidgetItem(sug_album or current_album or ''))
            self._apply_btn.setEnabled(True)

        self._fill_workers()

        if not self._pending and self._active == 0:
            self._status.setText(
                f"Done — {self._table.rowCount()} suggestion(s) found out of {self._total} tabs"
            )

    def _apply_selected(self):
        all_tabs = {t[0]: t for t in self.db_manager.get_all_tabs()}
        applied  = 0
        for row in range(self._table.rowCount()):
            chk = self._table.item(row, 0)
            if not (chk and chk.checkState() == Qt.Checked):
                continue
            tab_id = self._table.item(row, 1).data(Qt.UserRole)
            if tab_id not in all_tabs:
                continue
            t = all_tabs[tab_id]
            # t: id, band, album, title, tuning, rating, genre, notes
            tab_data = {
                "band":   self._table.item(row, 1).text(),
                "album":  self._table.item(row, 5).text(),
                "title":  self._table.item(row, 3).text(),
                "tuning": t[4], "rating": t[5],
                "genre":  t[6], "notes":  t[7],
            }
            try:
                self.db_manager.update_tab(tab_id, tab_data)
                applied += 1
            except Exception as e:
                print(f"Error updating tab {tab_id}: {e}")

        if applied and hasattr(self.parent(), 'load_data'):
            self.parent().load_data(preserve_tab=True)
        QMessageBox.information(self, "Applied", f"Updated {applied} tab(s).")


# ---------------------------------------------------------------------------
# Non-modal suggestion bar  (slides in at bottom of main window)
# ---------------------------------------------------------------------------
class NonModalSuggestionBar(QFrame):
    def __init__(self, band, title, tab_id, suggestion, db_manager, parent=None):
        super().__init__(parent)
        self._db_manager = db_manager
        self._tab_id     = tab_id
        self._suggestion = suggestion

        self.setObjectName("suggestionBar")
        self.setStyleSheet("""
            QFrame#suggestionBar {
                background-color: #1e3a5f;
                border-top: 2px solid #4a7abf;
            }
            QLabel { color: #e0e0e0; background: transparent; }
        """)
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)

        parts = []
        if suggestion.get('band') and suggestion['band'].lower() != band.lower():
            parts.append(f"Band: <b>{suggestion['band']}</b>")
        if suggestion.get('title') and suggestion['title'].lower() != title.lower():
            parts.append(f"Title: <b>{suggestion['title']}</b>")
        if suggestion.get('album'):
            parts.append(f"Album: <b>{suggestion['album']}</b>")
        if suggestion.get('tuning'):
            parts.append(f"Tuning: <b>{suggestion['tuning']}</b>")

        lbl = QLabel("Google suggests:  " + "  |  ".join(parts))
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)
        layout.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(70)
        apply_btn.clicked.connect(self._apply)
        layout.addWidget(apply_btn)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setFixedWidth(70)
        dismiss_btn.clicked.connect(self._dismiss)
        layout.addWidget(dismiss_btn)

    def _apply(self):
        try:
            all_tabs = {t[0]: t for t in self._db_manager.get_all_tabs()}
            if self._tab_id in all_tabs:
                t = all_tabs[self._tab_id]
                tab_data = {
                    "band":   self._suggestion.get('band',   t[1]),
                    "album":  self._suggestion.get('album',  t[2]),
                    "title":  self._suggestion.get('title',  t[3]),
                    "tuning": self._suggestion.get('tuning', t[4]),
                    "rating": t[5], "genre": t[6], "notes": t[7],
                }
                self._db_manager.update_tab(self._tab_id, tab_data)
                if hasattr(self.parent(), 'load_data'):
                    self.parent().load_data(preserve_tab=True)
        except Exception as e:
            print(f"Suggestion apply error: {e}")
        self._dismiss()

    def _dismiss(self):
        cb = getattr(self, '_dismiss_callback', None)
        if cb:
            cb()
        else:
            self.hide()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class GuitarTabApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GuitarTabs")
        self.setMinimumSize(1400, 800)
        self.drag_position = None

        # When frozen by PyInstaller, __file__ points into the temp _MEIPASS
        # folder which is deleted on exit. Use sys.executable so the database
        # is stored next to the .exe and persists between launches.
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path      = os.path.join(app_dir, "guitar_tabs.db")
        self.settings_path = os.path.join(app_dir, "settings.json")
        self.db_manager   = DatabaseManager(self.db_path)
        self._settings    = self._load_settings()
        self._title_checker  = TitleChecker(self)
        self._suggestion_bar = None

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

        self.pitch_shifter_btn = QPushButton("Pitch Calculator")
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

        self.add_tab_btn = QPushButton()
        self.add_tab_btn.setIcon(_load_icon_white("Images/Icons/plus.svg", 22))
        self.add_tab_btn.setIconSize(self.add_tab_btn.sizeHint())
        self.add_tab_btn.setFixedSize(36, 32)
        self.add_tab_btn.setToolTip("Add Tab")
        self.add_tab_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 4px; }"
            "QPushButton:hover { background: #3a3a3e; border-radius: 4px; }"
        )
        self.add_tab_btn.clicked.connect(self.show_add_dialog)
        action_layout.addWidget(self.add_tab_btn)

        action_layout.addSpacing(4)

        self.menu_btn = QPushButton()
        self.menu_btn.setIcon(_load_icon_white("Images/Icons/menue.svg", 22))
        self.menu_btn.setIconSize(self.menu_btn.sizeHint())
        self.menu_btn.setFixedSize(36, 32)
        self.menu_btn.setToolTip("Menu")
        self.menu_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 4px; }"
            "QPushButton:hover { background: #3a3a3e; border-radius: 4px; }"
        )
        self.menu_btn.clicked.connect(self._show_hamburger_menu)
        action_layout.addWidget(self.menu_btn)

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

        # Row height — 1.5× the default so rows are more readable
        vh = table.verticalHeader()
        vh.setDefaultSectionSize(int(vh.defaultSectionSize() * 1.5))

        table.hideColumn(0)
        table.setSortingEnabled(True)
        header.setSortIndicator(1, Qt.AscendingOrder)
        proxy.sort(1, Qt.AscendingOrder)
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
            "Rating", "Genre", "Notes", "Open with"
        ]

        all_tabs = self.db_manager.get_all_tabs()
        if all_tabs:
            self.tabs_widget.addTab(self._build_table_view(all_tabs, columns), "All Tabs")

        general_tabs    = []
        bands_with_few  = set()

        for band_id, band_name in bands:
            band_tabs = self.db_manager.get_tabs_for_band(band_id)
            if len(band_tabs) < self._settings['band_tab_threshold']:
                general_tabs.extend(band_tabs)
                bands_with_few.add(band_name)
            elif band_tabs:
                self.tabs_widget.addTab(self._build_table_view(band_tabs, columns), band_name)

        if general_tabs:
            t = self._build_table_view(general_tabs, columns)
            t.setToolTip(f"Bands with fewer than {self._settings['band_tab_threshold']} songs: {', '.join(sorted(bands_with_few))}")
            self.tabs_widget.insertTab(1, t, "General")

    def _load_learned_tabs_view(self):
        # data: (id, band, album, title, tuning, rating, genre, notes, learned_date)
        columns = [
            "ID", "Band", "Album", "Title", "Tuning",
            "Rating", "Genre", "Notes", "Learned Date", "Open with"
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
            if len(tabs) < self._settings['band_tab_threshold']:
                general.extend(tabs)
                bands_with_few.add(band_name)
            else:
                self.tabs_widget.addTab(self._build_table_view(tabs, columns), band_name)

        if general:
            t = self._build_table_view(general, columns)
            t.setToolTip(
                f"Bands with fewer than {self._settings['band_tab_threshold']} learned songs: {', '.join(sorted(bands_with_few))}"
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
        self._ug_delegate   = OpenWithDelegate(self)
        self._star_delegate = StarRatingDelegate(self)

        for i in range(self.tabs_widget.count()):
            table = self.tabs_widget.widget(i)
            if not isinstance(table, QTableView):
                continue

            source_model = table.model().sourceModel()
            try:
                col = source_model.columns.index("Open with")
                table.setItemDelegateForColumn(col, self._ug_delegate)
                table.setColumnWidth(col, 80)
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
            except ValueError:
                pass
            try:
                source_model.searchTabRequested.disconnect(self.searchTabOnline)
            except TypeError:
                pass
            source_model.searchTabRequested.connect(self.searchTabOnline)

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

    def searchOnSpotify(self, band, title):
        try:
            encoded = urllib.parse.quote(f"{band} {title}")
            webbrowser.open(f"https://open.spotify.com/search/{encoded}")
            self.statusBar().showMessage(f"Searching '{band} – {title}' on Spotify…")
        except Exception as e:
            self.statusBar().showMessage(f"Error opening Spotify: {e}")

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

            # ── Open with UG / Spotify (single row only) ──────────────
            ug_action = sp_action = None
            if n == 1:
                proxy_idx    = selected_rows[0]
                src_row      = current_tab.model().mapToSource(proxy_idx).row()
                src_model    = current_tab.model().sourceModel()
                _band  = src_model.get_row(src_row)[1]
                _title = src_model.get_row(src_row)[3]
                ug_action = menu.addAction(
                    _svg_to_icon("ultimate-guitar.svg", 16), "Open on Ultimate Guitar"
                )
                sp_action = menu.addAction(
                    _svg_to_icon("spotify-svgrepo-com.svg", 16), "Open on Spotify"
                )
                menu.addSeparator()

            if self.current_view == "all":
                learned_action = menu.addAction(
                    f"Mark {n} as Learned" if n > 1 else "Mark as Learned"
                )
            else:
                remove_action = menu.addAction(
                    f"Remove {n} from Learned" if n > 1 else "Remove from Learned"
                )

            menu.addSeparator()
            edit_action = menu.addAction("Edit Tab")
            if n > 1:
                edit_action.setEnabled(False)
                edit_action.setToolTip("Select a single tab to edit")
            set_rating_action = menu.addAction(f"Set Rating for {n} Tabs" if n > 1 else "Set Rating")
            delete_action     = menu.addAction(f"Delete {n} Tab(s)" if n > 1 else "Delete Tab")

            action = menu.exec_(current_tab.viewport().mapToGlobal(position))
            if action is None:
                return

            if action == ug_action and ug_action is not None:
                self.searchTabOnline(_band, _title)
            elif action == sp_action and sp_action is not None:
                self.searchOnSpotify(_band, _title)
            elif self.current_view == "all" and action == learned_action:
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
            row_data   = proxy.sourceModel().get_row(source_row)

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
                tab_id     = source_model.get_row(source_row)[0]
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
                tab_title = source_model.get_row(source_row)[3]
            try:
                if self.db_manager.add_to_learned(source_model.get_row(source_row)[0]):
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
            last_title = source_model.get_row(source_row)[3]
            try:
                self.db_manager.remove_from_learned(source_model.get_row(source_row)[0])
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
                if si.isValid() and 0 <= si.row() < source_model.rowCount():
                    tab_ids.append(source_model.get_row(si.row())[0])

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
        from add_tab_wizard import AddTabWizard
        wizard = AddTabWizard(self.db_manager, self)
        if wizard.exec_() != QDialog.Accepted:
            return

        success = duplicate = error = 0
        for tab_data in wizard.result_tabs:
            try:
                if self.db_manager.tab_exists(
                    tab_data["band"], tab_data["album"], tab_data["title"]
                ):
                    duplicate += 1
                    continue
                self.db_manager.add_tab(tab_data)
                success += 1
            except ValueError:
                duplicate += 1
            except Exception as e:
                error += 1
                print(f"Error adding tab: {e}")

        if success > 0:
            self.load_data(preserve_tab=True)
        msg = f"Added {success} tab(s)"
        if duplicate: msg += f", {duplicate} duplicate(s) skipped"
        if error:     msg += f", {error} error(s)"
        self.statusBar().showMessage(msg)

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
    # Suggestion bar helpers
    # ------------------------------------------------------------------
    def _show_suggestion_bar(self, band, title, tab_id, suggestion):
        self._dismiss_suggestion_bar()
        bar = NonModalSuggestionBar(band, title, tab_id, suggestion, self.db_manager, self)
        bar._dismiss_callback = self._dismiss_suggestion_bar
        self._suggestion_bar = bar
        self.centralWidget().layout().addWidget(bar)

    def _dismiss_suggestion_bar(self):
        if self._suggestion_bar:
            self.centralWidget().layout().removeWidget(self._suggestion_bar)
            self._suggestion_bar.deleteLater()
            self._suggestion_bar = None

    def _on_add_suggestion(self, band, title, tab_id, data):
        if data:
            self._show_suggestion_bar(band, title, tab_id, data)

    # ------------------------------------------------------------------
    # Bulk checker
    # ------------------------------------------------------------------
    def _open_bulk_checker(self):
        dlg = BulkCheckerDialog(self.db_manager, self._title_checker, self)
        dlg.exec_()

    # ------------------------------------------------------------------
    # Hamburger menu
    # ------------------------------------------------------------------
    def _show_hamburger_menu(self):
        menu = QMenu(self)
        menu.addAction("Add Multiple Tabs", self.show_batch_add_dialog)
        menu.addSeparator()

        import_menu = menu.addMenu("Import")
        import_menu.addAction("Import CSV", self.import_from_csv)
        import_menu.addAction("Import DB",  self.import_database)

        export_menu = menu.addMenu("Export")
        export_menu.addAction("Export CSV", self.export_to_csv)
        export_menu.addAction("Export DB",  self.backup_database)

        menu.addSeparator()
        menu.addAction("Settings", self.show_settings)

        menu.exec_(self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height())))

    # ------------------------------------------------------------------
    # Settings — load / save / dialog
    # ------------------------------------------------------------------
    def _load_settings(self):
        defaults = {'band_tab_threshold': 5}
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                defaults.update(data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return defaults

    def _save_settings(self):
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=2)

    def show_settings(self):
        from PyQt5.QtWidgets import QListWidget, QStackedWidget

        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setMinimumSize(500, 320)

        outer = QVBoxLayout(dlg)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Two-panel area ────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        # Left nav
        nav = QListWidget()
        nav.setFixedWidth(130)
        nav.addItems(["General", "Database"])
        nav.setCurrentRow(0)
        nav.setStyleSheet("""
            QListWidget {
                background: #1c1c20;
                border: none;
                border-right: 1px solid #3a3a3e;
                padding-top: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 18px;
                color: #bbbbbb;
                border: none;
            }
            QListWidget::item:selected {
                background: #2e2e34;
                color: #ffffff;
                border-left: 3px solid #e3ac63;
                padding-left: 15px;
            }
        """)

        # Right stacked content
        stack = QStackedWidget()
        stack.setStyleSheet("background: #26262b;")

        # ── Page: General ─────────────────────────────────────────────
        page_general = QWidget()
        lay_gen = QVBoxLayout(page_general)
        lay_gen.setContentsMargins(24, 20, 24, 20)
        lay_gen.setSpacing(14)

        lbl_gen = QLabel("General")
        lbl_gen.setStyleSheet(
            "color: #888888; font-weight: bold; font-size: 12px; letter-spacing: 1px;"
        )
        lay_gen.addWidget(lbl_gen)

        sep_gen = QFrame()
        sep_gen.setFrameShape(QFrame.HLine)
        sep_gen.setStyleSheet("color: #3a3a3e;")
        lay_gen.addWidget(sep_gen)

        form_gen = QFormLayout()
        form_gen.setSpacing(10)
        spin = QSpinBox()
        spin.setRange(1, 100)
        spin.setValue(self._settings['band_tab_threshold'])
        spin.setToolTip(
            "A band gets its own tab when it has at least this many songs.\n"
            "Bands below this number appear in the 'General' tab."
        )
        form_gen.addRow("Min songs for own tab:", spin)
        lay_gen.addLayout(form_gen)
        lay_gen.addStretch()

        # ── Page: Database ────────────────────────────────────────────
        page_db = QWidget()
        lay_db = QVBoxLayout(page_db)
        lay_db.setContentsMargins(24, 20, 24, 20)
        lay_db.setSpacing(10)

        lbl_db = QLabel("Database")
        lbl_db.setStyleSheet(
            "color: #888888; font-weight: bold; font-size: 12px; letter-spacing: 1px;"
        )
        lay_db.addWidget(lbl_db)

        sep_db = QFrame()
        sep_db.setFrameShape(QFrame.HLine)
        sep_db.setStyleSheet("color: #3a3a3e;")
        lay_db.addWidget(sep_db)

        n_tabs  = len(self.db_manager.get_all_tabs())
        est_min = max(1, round(n_tabs * 1.1 / 60))

        desc = QLabel(
            "Compares every tab against MusicBrainz and suggests\n"
            "corrections for title, band name, or album."
        )
        desc.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        lay_db.addWidget(desc)

        check_btn = QPushButton("Check All Entries…")
        check_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a42;
                color: #ffffff;
                border: 1px solid #555560;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QPushButton:hover  { background-color: #4a4a54; border-color: #888890; }
            QPushButton:pressed { background-color: #2a2a30; }
        """)
        check_btn.setToolTip(
            f"Queries MusicBrainz for all {n_tabs} tabs.\n"
            f"Rate-limited to 1 req/sec — takes ~{est_min} min.\n"
            "Progress is shown in the checker window."
        )
        check_btn.clicked.connect(self._open_bulk_checker)
        lay_db.addWidget(check_btn)

        warning = QLabel(f"⚠  {n_tabs} tab(s) queued — estimated ~{est_min} min")
        warning.setStyleSheet("color: #e3ac63; font-size: 10px;")
        lay_db.addWidget(warning)
        lay_db.addStretch()

        stack.addWidget(page_general)
        stack.addWidget(page_db)
        nav.currentRowChanged.connect(stack.setCurrentIndex)

        body.addWidget(nav)
        body.addWidget(stack, 1)
        outer.addLayout(body, 1)

        # ── Dialog buttons ────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(12, 8, 12, 12)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        btn_bar.addStretch()
        btn_bar.addWidget(buttons)
        outer.addLayout(btn_bar)

        if dlg.exec_() == QDialog.Accepted:
            self._settings['band_tab_threshold'] = spin.value()
            self._save_settings()
            self.load_data(preserve_tab=False)
            self.statusBar().showMessage(
                f"Settings saved — own tab from {spin.value()} songs"
            )

    # ------------------------------------------------------------------
    # Import CSV  (single .csv or .zip bundle)
    # ------------------------------------------------------------------
    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import", "",
            "Supported Files (*.zip *.csv);;ZIP Bundle (*.zip);;CSV File (*.csv);;All Files (*)"
        )
        if not file_path:
            return
        if file_path.lower().endswith(".zip"):
            self._import_zip(file_path)
        else:
            success, duplicate, error = self._import_tabs_csv(file_path)
            self.load_data(preserve_tab=True)
            msg = f"Imported {success} tab(s)"
            if duplicate: msg += f", {duplicate} duplicate(s) skipped"
            if error:     msg += f", {error} error(s)"
            self.statusBar().showMessage(msg)

    def _import_tabs_csv(self, file_path_or_text, is_text=False):
        """Import tabs from a CSV file path or raw text. Returns (success, duplicate, error)."""
        success = duplicate = error = 0
        f_handle = None
        try:
            if is_text:
                reader = csv.DictReader(io.StringIO(file_path_or_text))
            else:
                f_handle = open(file_path_or_text, "r", encoding="utf-8-sig")
                reader = csv.DictReader(f_handle)
            for row in reader:
                try:
                    row = {k.lower().strip(): v for k, v in row.items()}
                    band  = row.get("band",  "").strip()
                    title = row.get("title", "").strip()
                    if not band or not title:
                        continue
                    album  = row.get("album",  "").strip()
                    tuning = row.get("tuning", "").strip()
                    genre  = row.get("genre",  "").strip()
                    notes  = row.get("notes",  "").strip()
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
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Import Error", str(e))
        finally:
            if f_handle:
                f_handle.close()
        return success, duplicate, error

    def _import_tunings_csv(self, text):
        added = 0
        try:
            for row in csv.DictReader(io.StringIO(text)):
                row = {k.lower().strip(): v for k, v in row.items()}
                name = row.get("tuning", "").strip()
                if not name:
                    continue
                try:
                    is_seven = bool(int(row.get("is_seven_string", 0)))
                except (ValueError, TypeError):
                    is_seven = False
                try:
                    self.db_manager.add_tuning(name, is_seven)
                    added += 1
                except Exception:
                    pass
        except Exception as e:
            print(f"Tunings import error: {e}")
        return added

    def _import_learned_csv(self, text):
        marked = 0
        try:
            for row in csv.DictReader(io.StringIO(text)):
                row = {k.lower().strip(): v for k, v in row.items()}
                band  = row.get("band",  "").strip()
                title = row.get("title", "").strip()
                album = row.get("album", "").strip()
                learned_date = row.get("learned date", "").strip()
                if not band or not title:
                    continue
                tab_id = self.db_manager.get_tab_id(band, album, title)
                if tab_id and not self.db_manager.is_learned(tab_id):
                    self.db_manager.mark_as_learned(tab_id)
                    if learned_date:
                        self.db_manager.update_learned_date(tab_id, learned_date)
                    marked += 1
        except Exception as e:
            print(f"Learned import error: {e}")
        return marked

    def _import_zip(self, zip_path):
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                tabs_ok = dup = err = tunings_added = learned_marked = 0
                if "tabs.csv" in names:
                    text = zf.read("tabs.csv").decode("utf-8-sig")
                    tabs_ok, dup, err = self._import_tabs_csv(text, is_text=True)
                if "tunings.csv" in names:
                    text = zf.read("tunings.csv").decode("utf-8-sig")
                    tunings_added = self._import_tunings_csv(text)
                if "learned_tabs.csv" in names:
                    text = zf.read("learned_tabs.csv").decode("utf-8-sig")
                    learned_marked = self._import_learned_csv(text)
            self.load_data(preserve_tab=True)
            parts = [f"{tabs_ok} tab(s) imported"]
            if dup:            parts.append(f"{dup} duplicate(s) skipped")
            if err:            parts.append(f"{err} error(s)")
            if tunings_added:  parts.append(f"{tunings_added} tuning(s) added")
            if learned_marked: parts.append(f"{learned_marked} tab(s) marked learned")
            self.statusBar().showMessage(", ".join(parts))
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Import Failed", str(e))

    # ------------------------------------------------------------------
    # Import DB
    # ------------------------------------------------------------------
    def import_database(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Database", "", "SQLite Database (*.db);;All Files (*)"
        )
        if not file_path:
            return
        reply = QMessageBox.warning(
            self, "Replace Database",
            "This will replace your current database with the selected file.\n"
            "All current data will be overwritten.\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.copy2(file_path, self.db_path)
            self.db_manager = DatabaseManager(self.db_path)
            self.load_data()
            self.statusBar().showMessage("Database imported successfully")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Import Failed", str(e))

    # ------------------------------------------------------------------
    # Export CSV — exports everything as a ZIP (tabs + learned + tunings)
    # ------------------------------------------------------------------
    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "guitar_tabs_export.zip",
            "ZIP Bundle (*.zip);;All Files (*)"
        )
        if not file_path:
            return
        try:
            tabs_data    = self.db_manager.get_all_tabs()
            learned_data = self.db_manager.get_all_learned_tabs()
            tunings_6    = self.db_manager.get_all_tunings(seven_string=False)
            tunings_7    = self.db_manager.get_all_tunings(seven_string=True)

            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # tabs.csv
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["band", "album", "title", "tuning", "rating", "genre", "notes"])
                for row in tabs_data:
                    w.writerow(row[1:])
                zf.writestr("tabs.csv", buf.getvalue())

                # learned_tabs.csv
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["band", "album", "title", "tuning", "rating", "genre", "notes", "learned date"])
                for row in learned_data:
                    w.writerow(row[1:])
                zf.writestr("learned_tabs.csv", buf.getvalue())

                # tunings.csv
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["tuning", "is_seven_string"])
                for t in tunings_6:
                    w.writerow([t, 0])
                for t in tunings_7:
                    w.writerow([t, 1])
                zf.writestr("tunings.csv", buf.getvalue())

            self.statusBar().showMessage(
                f"Exported {len(tabs_data)} tab(s) to {os.path.basename(file_path)}"
            )
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Failed", str(e))

    # ------------------------------------------------------------------
    # Export DB (save a copy of the database file)
    # ------------------------------------------------------------------
    def backup_database(self):
        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"guitar_tabs_backup_{timestamp}.db"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Database", default_name,
            "SQLite Database (*.db);;All Files (*)"
        )
        if not file_path:
            return
        try:
            shutil.copy2(self.db_path, file_path)
            self.statusBar().showMessage(f"Database saved to {os.path.basename(file_path)}")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Failed", str(e))

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

        title_label = QLabel("GuitarTabs")
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

    def _tb_mouse_release(self, _event):
        self.drag_position = None
