"""
Add Tabs Wizard  —  guided 4-step flow via MusicBrainz + Ultimate Guitar.

  Step 1  Search artist, pick from results
  Step 2  Pick a studio album  (or skip / enter manually)
  Step 3  Tick tracks to add
  Step 4  Review: per-song tuning auto-looked-up from Ultimate Guitar (editable)
          + global rating / genre before final add

After accept(), iterate self.result_tabs for the ready-to-save dicts.
"""
import gzip
import html as _html
import re
import ssl
import json
import time
import urllib.request
import urllib.parse

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QCheckBox,
    QComboBox, QStackedWidget, QFrame, QFormLayout, QWidget,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from add_tab_dialog import StarRating

_MB_BASE          = "https://musicbrainz.org/ws/2"
_MB_USER_AGENT    = "GuitarTabCollection/1.0 (music-metadata-lookup)"
_UNWANTED_SECONDARY = frozenset({
    'live', 'compilation', 'remix', 'dj-mix',
    'mixtape/street', 'demo', 'interview', 'broadcast',
})

_DARK_LIST_STYLE = """
    QListWidget {
        background-color: #1e1e22;
        border: 1px solid #3a3a3e;
        color: #e0e0e0;
        alternate-background-color: #252529;
        outline: none;
    }
    QListWidget::item { padding: 4px 6px; }
    QListWidget::item:selected {
        background-color: #3a5a8a;
        color: #ffffff;
    }
    QListWidget::item:hover:!selected { background-color: #2e2e34; }
"""

_TABLE_DARK_STYLE = """
    QTableWidget {
        background-color: #1e1e22;
        alternate-background-color: #252529;
        color: #e0e0e0;
        gridline-color: #3a3a3e;
        border: 1px solid #3a3a3e;
    }
    QTableWidget::item { padding: 3px 5px; }
    QTableWidget::item:selected { background-color: #3a5a8a; color: #fff; }
    QHeaderView::section {
        background-color: #2a2a2e;
        color: #b0b0b0;
        border: none;
        border-right: 1px solid #3a3a3e;
        padding: 4px 6px;
    }
    QScrollBar:vertical {
        background: #1a1a1e; width: 10px;
    }
    QScrollBar::handle:vertical { background: #4a4a52; border-radius: 4px; }
"""

_COMBO_CELL_STYLE = """
    QComboBox {
        background-color: #1e1e22;
        border: 1px solid #3a3a3e;
        color: #e0e0e0;
        padding: 1px 4px;
        combobox-popup: 0;
    }
    QComboBox QAbstractItemView {
        background-color: #1e1e22;
        color: #e0e0e0;
        selection-background-color: #3a5a8a;
    }
"""

# Browser-like User-Agent for Ultimate Guitar
_SONGSTERR_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# (No tuning helpers needed — Ultimate Guitar returns plain strings like "E A D G B E")


# ---------------------------------------------------------------------------
# Custom list widget — clicking anywhere on a checkable row toggles it
# ---------------------------------------------------------------------------
class _TrackListWidget(QListWidget):
    """
    Overrides mousePressEvent so that clicking the track title (not just the
    tiny checkbox indicator) also toggles the checked state.
    """
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is not None and (item.flags() & Qt.ItemIsUserCheckable):
            rect = self.visualItemRect(item)
            # The checkbox indicator sits at the very left of the item;
            # its width is approximately equal to the item's height.
            indicator_right = rect.left() + rect.height()
            if event.x() > indicator_right:
                # Click landed on the text label — toggle manually.
                # super() will handle selection but won't touch the checkbox
                # because the pointer is past the indicator area.
                new_state = (Qt.Unchecked
                             if item.checkState() == Qt.Checked
                             else Qt.Checked)
                item.setCheckState(new_state)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Shared MusicBrainz helper
# ---------------------------------------------------------------------------
def _mb_get(endpoint, params):
    """Rate-limited (1.1 s) MusicBrainz GET — returns parsed JSON."""
    time.sleep(1.1)
    url = f"{_MB_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": _MB_USER_AGENT})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------
class _ArtistSearchWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            data = _mb_get("artist", {"query": self.query, "fmt": "json", "limit": "10"})
            self.done.emit(data.get("artists", []))
        except Exception:
            self.done.emit([])


class _AlbumListWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, artist_id):
        super().__init__()
        self.artist_id = artist_id

    def run(self):
        try:
            albums, offset = [], 0
            while True:
                data = _mb_get("release-group", {
                    "artist": self.artist_id, "type": "album",
                    "fmt": "json", "limit": "100", "offset": str(offset),
                })
                rgs = data.get("release-groups", [])
                albums.extend(rgs)
                offset += 100
                if offset >= data.get("release-group-count", 0) or not rgs:
                    break

            studio = [
                rg for rg in albums
                if rg.get("primary-type", "").lower() == "album"
                and not ({t.lower() for t in rg.get("secondary-types", [])} & _UNWANTED_SECONDARY)
            ]
            studio.sort(key=lambda r: r.get("first-release-date", "") or "9999")
            self.done.emit(studio)
        except Exception:
            self.done.emit([])


class _TrackListWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, rg_id):
        super().__init__()
        self.rg_id = rg_id

    def run(self):
        try:
            # ── Step 1: look up the release-group to get its releases ──
            rg_data = _mb_get(f"release-group/{self.rg_id}", {
                "inc": "releases",
                "fmt": "json",
            })
            releases = rg_data.get("releases", [])
            if not releases:
                self.done.emit([])
                return

            # Pick the earliest official release; fall back to any
            official = sorted(
                [r for r in releases if r.get("status", "").lower() == "official"],
                key=lambda r: r.get("date", "9999") or "9999",
            )
            target_id = (official or releases)[0]["id"]

            # ── Step 2: fetch the full track listing for that release ──
            detail = _mb_get(f"release/{target_id}", {
                "inc": "recordings",
                "fmt": "json",
            })
            tracks = []
            for medium in detail.get("media", []):
                for track in medium.get("tracks", []):
                    title = track.get("title", "").strip()
                    if title:
                        tracks.append(title)
            self.done.emit(tracks)
        except Exception:
            self.done.emit([])


class _TuningLookupWorker(QThread):
    """
    Looks up guitar tuning via Ultimate Guitar's embedded JSON store.

    UG search pages include a <div class="js-store" data-content="..."> element
    whose HTML-escaped value is a JSON blob containing all tab results, each
    with a 'tuning' field (e.g. "E A D G B E").  No API key required.
    """
    done = pyqtSignal(int, str, bool)   # row, tuning, is_seven

    _HEADERS = {
        "User-Agent":      _SONGSTERR_UA,
        "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, row, artist, title):
        super().__init__()
        self.row    = row
        self.artist = artist
        self.title  = title

    def run(self):
        try:
            tuning, is_seven = self._fetch()
        except Exception:
            tuning, is_seven = "", False
        self.done.emit(self.row, tuning, is_seven)

    def _fetch_html(self, url, ctx):
        """GET url, decompress gzip if needed, return decoded HTML string."""
        req = urllib.request.Request(url, headers=self._HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            encoding = r.headers.get("Content-Encoding", "")
            raw      = r.read()
        if "gzip" in encoding:
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="ignore")

    def _fetch(self):
        ctx = ssl.create_default_context()

        # ── Search UG — Guitar Pro tabs only (type=500) have tuning data ─
        params = urllib.parse.urlencode([
            ("title",   self.title),
            ("artist",  self.artist),
            ("page",    "1"),
            ("type[]",  "500"),   # 500 = Guitar Pro — always includes tuning
        ])
        html_text = self._fetch_html(
            f"https://www.ultimate-guitar.com/search.php?{params}", ctx
        )

        results = self._extract_results(html_text)

        # Fall back to a generic search if GP search returned nothing
        if not results:
            params2 = urllib.parse.urlencode({
                "title":  self.title,
                "artist": self.artist,
                "page":   "1",
            })
            html_text = self._fetch_html(
                f"https://www.ultimate-guitar.com/search.php?{params2}", ctx
            )
            results = self._extract_results(html_text)

        if not results:
            return "", False

        artist_lower = self.artist.lower()
        title_lower  = self.title.lower()

        # Pass 1 — exact artist + title, has tuning
        for tab in results:
            if (tab.get("artist_name", "").lower() == artist_lower
                    and tab.get("song_name", "").lower() == title_lower
                    and tab.get("tuning", "").strip()):
                return self._parse(tab["tuning"])

        # Pass 2 — exact artist, any title, has tuning
        for tab in results:
            if (tab.get("artist_name", "").lower() == artist_lower
                    and tab.get("tuning", "").strip()):
                return self._parse(tab["tuning"])

        # Pass 3 — any result with a tuning
        for tab in results:
            if tab.get("tuning", "").strip():
                return self._parse(tab["tuning"])

        return "", False

    @staticmethod
    def _extract_results(html_text):
        """
        Pull the tab result list from UG's embedded JSON store.
        UG embeds all page data as HTML-escaped JSON inside a data-content
        attribute.  We try a loose regex first, then a tight one as fallback,
        and walk several known JSON paths to find the results list.
        """
        # Flexible regex: handles any attribute order inside the div tag,
        # and also catches any large data-content blob as a last resort.
        patterns = [
            r'class="js-store"[^>]*data-content="([^"]+)"',
            r'data-content="([^"]+)"[^>]*class="js-store"',
            r'data-content="([^"]{200,})"',   # any large blob on the page
        ]
        raw = None
        for pat in patterns:
            m = re.search(pat, html_text)
            if m:
                raw = m.group(1)
                break
        if not raw:
            return []

        try:
            data = json.loads(_html.unescape(raw))
        except (ValueError, TypeError):
            return []

        # Try several known JSON paths UG has used over the years
        candidates = [
            lambda d: d["store"]["page"]["data"]["results"],
            lambda d: d["store"]["page"]["data"]["tabs"],
            lambda d: d["data"]["results"],
            lambda d: d["data"]["tabs"],
            lambda d: d["results"],
            lambda d: d["tabs"],
        ]
        for fn in candidates:
            try:
                r = fn(data)
                if isinstance(r, list) and r:
                    return r
            except (KeyError, TypeError):
                continue
        return []

    @staticmethod
    def _parse(tuning_str):
        t = tuning_str.strip()
        return t, len(t.split()) == 7


# ---------------------------------------------------------------------------
# Wizard dialog
# ---------------------------------------------------------------------------
class AddTabWizard(QDialog):
    """
    Guided 4-step dialog for adding tabs via MusicBrainz + Songsterr.
    After accept(), iterate self.result_tabs for tab data dicts.
    """

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Tabs")
        self.setMinimumSize(640, 600)

        self.db_manager   = db_manager
        self.result_tabs  = []
        self._artist_id   = ""
        self._artist_name = ""
        self._album_id    = ""
        self._album_title = ""
        self._workers     = []
        # Per-row widgets on the review page
        self._row_tuning_combos = []
        self._row_seven_checks  = []

        # ── Global dark styling ────────────────────────────────────────
        self.setStyleSheet(_DARK_LIST_STYLE + """
            QLineEdit {
                background-color: #1e1e22;
                border: 1px solid #3a3a3e;
                color: #e0e0e0;
                padding: 4px 6px;
                border-radius: 3px;
            }
            QLineEdit:focus { border-color: #6a9fd8; }
            QCheckBox { color: #e0e0e0; }
            QLabel    { color: #e0e0e0; }
        """)

        # ── Outer layout ───────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 12)
        outer.setSpacing(6)

        self._step_lbl = QLabel()
        f = QFont(); f.setBold(True)
        self._step_lbl.setFont(f)
        self._step_lbl.setStyleSheet("color: #e3ac63;")
        outer.addWidget(self._step_lbl)

        # Loading bar — indeterminate, hidden when idle
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(5)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar           { border: none; background: #1a1a1e; }
            QProgressBar::chunk   { background: #e3ac63; border-radius: 2px; }
        """)
        self._progress.setVisible(False)
        outer.addWidget(self._progress)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #3a3a3e;")
        outer.addWidget(sep)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #888888; font-size: 10px;")
        outer.addWidget(self._status_lbl)

        nav = QHBoxLayout()
        self._back_btn   = QPushButton("← Back")
        self._next_btn   = QPushButton("Next →")
        self._cancel_btn = QPushButton("Cancel")
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn.clicked.connect(self._go_next)
        self._cancel_btn.clicked.connect(self.reject)
        nav.addWidget(self._back_btn)
        nav.addStretch()
        nav.addWidget(self._cancel_btn)
        nav.addWidget(self._next_btn)
        outer.addLayout(nav)

        self._build_p0()
        self._build_p1()
        self._build_p2()
        self._build_p3()
        self._stack.setCurrentIndex(0)
        self._refresh_nav()

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------
    def _build_p0(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        row = QHBoxLayout()
        self._artist_edit = QLineEdit()
        self._artist_edit.setPlaceholderText("Artist / band name…")
        self._artist_edit.returnPressed.connect(self._do_artist_search)
        row.addWidget(self._artist_edit)
        self._search_btn = QPushButton("Search")
        self._search_btn.clicked.connect(self._do_artist_search)
        row.addWidget(self._search_btn)
        lay.addLayout(row)

        lay.addWidget(QLabel("Select the correct artist (double-click or select + Next):"))
        self._artist_list = QListWidget()
        self._artist_list.setAlternatingRowColors(True)
        self._artist_list.itemDoubleClicked.connect(self._go_next)
        lay.addWidget(self._artist_list, 1)
        self._stack.addWidget(w)

    def _build_p1(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        self._album_lbl = QLabel()
        lay.addWidget(self._album_lbl)

        self._album_list = QListWidget()
        self._album_list.setAlternatingRowColors(True)
        self._album_list.itemDoubleClicked.connect(self._go_next)
        lay.addWidget(self._album_list, 1)

        self._skip_album_chk = QCheckBox("Skip / enter album manually")
        self._skip_album_chk.toggled.connect(lambda s: self._album_list.setEnabled(not s))
        lay.addWidget(self._skip_album_chk)
        self._stack.addWidget(w)

    def _build_p2(self):
        """Step 3 — track selection only (no form; tuning moves to review step)."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        # Inner stack: track list (0) vs manual entry (1)
        self._inner_stack = QStackedWidget()
        lay.addWidget(self._inner_stack, 1)

        # ── Inner page 0: track list ──────────────────────────────────
        track_page = QWidget()
        tp_lay = QVBoxLayout(track_page)
        tp_lay.setContentsMargins(0, 0, 0, 0)
        tp_lay.setSpacing(4)
        self._track_header = QLabel("Select tracks to add:")
        tp_lay.addWidget(self._track_header)
        self._track_list = _TrackListWidget()
        self._track_list.setAlternatingRowColors(True)
        tp_lay.addWidget(self._track_list, 1)
        sel_row = QHBoxLayout()
        btn_all  = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_all.clicked.connect(lambda: self._set_all_tracks(True))
        btn_none.clicked.connect(lambda: self._set_all_tracks(False))
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        tp_lay.addLayout(sel_row)
        self._inner_stack.addWidget(track_page)

        # ── Inner page 1: manual entry ────────────────────────────────
        manual_page = QWidget()
        mp_lay = QFormLayout(manual_page)
        mp_lay.setContentsMargins(0, 8, 0, 0)
        mp_lay.setSpacing(8)
        self._manual_album = QLineEdit()
        self._manual_album.setPlaceholderText("Album name (optional)")
        self._manual_title = QLineEdit()
        self._manual_title.setPlaceholderText("Track title (required)")
        mp_lay.addRow("Album:", self._manual_album)
        mp_lay.addRow("Title:", self._manual_title)
        self._inner_stack.addWidget(manual_page)

        self._stack.addWidget(w)

    def _build_p3(self):
        """Step 4 — tuning review table (per song) + global rating / genre."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        hdr = QLabel(
            "Review suggested tunings (source: Ultimate Guitar) — "
            "click a tuning to edit, tick 7-str where needed."
        )
        hdr.setWordWrap(True)
        lay.addWidget(hdr)

        self._review_table = QTableWidget(0, 4)
        self._review_table.setHorizontalHeaderLabels(["Title", "Album", "Tuning", "7-str"])
        hh = self._review_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Interactive)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self._review_table.setColumnWidth(2, 160)
        self._review_table.setColumnWidth(3, 52)
        self._review_table.verticalHeader().setVisible(False)
        self._review_table.setAlternatingRowColors(True)
        self._review_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._review_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._review_table.setStyleSheet(_TABLE_DARK_STYLE)
        lay.addWidget(self._review_table, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #3a3a3e;")
        lay.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(6)

        self._rating_widget = StarRating()
        form.addRow("Rating (all):", self._rating_widget)

        self._genre_combo = QComboBox()
        self._genre_combo.setEditable(True)
        self._genre_combo.setInsertPolicy(QComboBox.NoInsert)
        self._genre_combo.setMaxVisibleItems(15)
        self._genre_combo.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self._genre_combo.addItem("")
        form.addRow("Genre (all):", self._genre_combo)

        lay.addLayout(form)
        self._stack.addWidget(w)
        self._load_genres()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_genres(self):
        genres = self.db_manager.get_all_genres()
        self._genre_combo.clear()
        self._genre_combo.addItem("")
        self._genre_combo.addItems(genres)
        self._genre_combo.setCurrentIndex(0)

    def _set_all_tracks(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self._track_list.count()):
            self._track_list.item(i).setCheckState(state)

    def _set_busy(self, busy, msg=""):
        self._progress.setVisible(busy)
        self._next_btn.setEnabled(not busy)
        self._back_btn.setEnabled(not busy and self._stack.currentIndex() > 0)
        self._status_lbl.setText(msg)

    def _refresh_nav(self):
        idx = self._stack.currentIndex()
        self._back_btn.setEnabled(idx > 0)
        self._next_btn.setText("Add All" if idx == 3 else "Next →")
        self._step_lbl.setText([
            "Step 1 of 4 — Search Artist",
            "Step 2 of 4 — Select Album",
            "Step 3 of 4 — Select Tracks",
            "Step 4 of 4 — Review Tunings",
        ][idx])

    def _go_back(self):
        idx = self._stack.currentIndex()
        if idx > 0:
            self._stack.setCurrentIndex(idx - 1)
            self._refresh_nav()
            self._status_lbl.setText("")

    def _go_next(self):
        idx = self._stack.currentIndex()
        if   idx == 0: self._advance_from_p0()
        elif idx == 1: self._advance_from_p1()
        elif idx == 2: self._advance_from_p2()
        elif idx == 3: self._collect_and_accept()

    def _remove_worker(self, w):
        try:
            self._workers.remove(w)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Step 1 — artist search
    # ------------------------------------------------------------------
    def _do_artist_search(self):
        query = self._artist_edit.text().strip()
        if not query:
            self._status_lbl.setText("Enter an artist name first.")
            return
        self._artist_list.clear()
        self._search_btn.setEnabled(False)
        self._set_busy(True, "Searching MusicBrainz…")
        w = _ArtistSearchWorker(query)
        self._workers.append(w)
        w.done.connect(lambda r, _w=w: self._on_artist_results(_w, r))
        w.start()

    def _on_artist_results(self, worker, artists):
        self._remove_worker(worker)
        self._search_btn.setEnabled(True)
        self._set_busy(False)
        self._artist_list.clear()

        if not artists:
            self._status_lbl.setText("No artists found — try a different spelling.")
            return

        query = self._artist_edit.text().strip().lower()

        exact  = [a for a in artists if a.get("name", "").lower() == query]
        others = [a for a in artists if a.get("name", "").lower() != query][:3]

        for a in (exact + others):
            name    = a.get("name", "")
            country = a.get("country", "")
            disamb  = a.get("disambiguation", "")
            parts   = [name]
            if country: parts.append(f"[{country}]")
            if disamb:  parts.append(f"({disamb})")
            item = QListWidgetItem("  ".join(parts))
            item.setData(Qt.UserRole,     a.get("id", ""))
            item.setData(Qt.UserRole + 1, name)
            if a.get("name", "").lower() == query:
                item.setForeground(QColor("#e3ac63"))
            self._artist_list.addItem(item)

        self._artist_list.setCurrentRow(0)
        total_shown = len(exact) + len(others)
        self._status_lbl.setText(
            f"Showing {total_shown} result(s) — "
            f"{len(exact)} exact match(es) highlighted."
        )

    def _advance_from_p0(self):
        item = self._artist_list.currentItem()
        if not item:
            self._status_lbl.setText("Select an artist from the list first.")
            return
        self._artist_id   = item.data(Qt.UserRole)
        self._artist_name = item.data(Qt.UserRole + 1)
        self._album_lbl.setText(f"Studio albums for  {self._artist_name}:")
        self._album_list.clear()
        self._skip_album_chk.setChecked(False)
        self._stack.setCurrentIndex(1)
        self._refresh_nav()
        self._load_albums()

    # ------------------------------------------------------------------
    # Step 2 — album selection
    # ------------------------------------------------------------------
    def _load_albums(self):
        self._set_busy(True, "Loading studio albums…")
        w = _AlbumListWorker(self._artist_id)
        self._workers.append(w)
        w.done.connect(lambda r, _w=w: self._on_album_results(_w, r))
        w.start()

    def _on_album_results(self, worker, albums):
        self._remove_worker(worker)
        self._set_busy(False)
        self._album_list.clear()
        if not albums:
            self._status_lbl.setText("No studio albums found — use 'Skip' to enter manually.")
            self._skip_album_chk.setChecked(True)
            return
        for rg in albums:
            title = rg.get("title", "")
            year  = (rg.get("first-release-date", "") or "")[:4]
            item  = QListWidgetItem(f"{title}  ({year})" if year else title)
            item.setData(Qt.UserRole,     rg.get("id", ""))
            item.setData(Qt.UserRole + 1, title)
            self._album_list.addItem(item)
        self._status_lbl.setText(f"{len(albums)} studio album(s) found.")

    def _advance_from_p1(self):
        skip = self._skip_album_chk.isChecked()
        if not skip:
            item = self._album_list.currentItem()
            if not item:
                self._status_lbl.setText("Select an album, or tick 'Skip'.")
                return
            self._album_id    = item.data(Qt.UserRole)
            self._album_title = item.data(Qt.UserRole + 1)
        else:
            self._album_id    = ""
            self._album_title = ""

        self._track_list.clear()
        self._manual_album.setText(self._album_title)
        self._manual_title.clear()
        self._inner_stack.setCurrentIndex(1 if skip else 0)
        self._stack.setCurrentIndex(2)
        self._refresh_nav()

        if not skip:
            self._track_header.setText(f"Tracks on  {self._album_title}:")
            self._load_tracks()
        else:
            self._status_lbl.setText("")

    # ------------------------------------------------------------------
    # Step 3 — track selection
    # ------------------------------------------------------------------
    def _load_tracks(self):
        self._set_busy(True, "Loading track listing (fetching release details)…")
        w = _TrackListWorker(self._album_id)
        self._workers.append(w)
        w.done.connect(lambda r, _w=w: self._on_track_results(_w, r))
        w.start()

    def _on_track_results(self, worker, tracks):
        self._remove_worker(worker)
        self._set_busy(False)
        self._track_list.clear()
        if not tracks:
            self._status_lbl.setText(
                "No track listing found on MusicBrainz — "
                "go back and choose 'Skip' to enter manually."
            )
            return
        for title in tracks:
            item = QListWidgetItem(title)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._track_list.addItem(item)
        self._status_lbl.setText(f"{len(tracks)} track(s) — tick the ones to add.")

    def _advance_from_p2(self):
        """Collect selected tracks → populate review table → start tuning lookups."""
        if self._inner_stack.currentIndex() == 1:
            # Manual entry: one song
            title = self._manual_title.text().strip()
            if not title:
                self._status_lbl.setText("Enter a track title.")
                return
            album = self._manual_album.text().strip()
            songs = [(title, album)]
        else:
            songs = [
                (self._track_list.item(i).text(), self._album_title)
                for i in range(self._track_list.count())
                if self._track_list.item(i).checkState() == Qt.Checked
            ]
            if not songs:
                self._status_lbl.setText("Tick at least one track.")
                return

        self._populate_review_table(songs)
        self._stack.setCurrentIndex(3)
        self._refresh_nav()
        self._start_tuning_lookups()

    # ------------------------------------------------------------------
    # Step 4 — review / tuning lookup
    # ------------------------------------------------------------------
    def _populate_review_table(self, songs):
        """songs: list of (title, album) tuples."""
        self._review_table.setRowCount(0)
        self._row_tuning_combos.clear()
        self._row_seven_checks.clear()

        six_tunings  = self.db_manager.get_all_tunings(seven_string=False)
        seven_tunings = self.db_manager.get_all_tunings(seven_string=True)

        for row, (title, album) in enumerate(songs):
            self._review_table.insertRow(row)

            # Title (read-only)
            ti = QTableWidgetItem(title)
            ti.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self._review_table.setItem(row, 0, ti)

            # Album (read-only)
            ai = QTableWidgetItem(album)
            ai.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self._review_table.setItem(row, 1, ai)

            # Tuning — editable combo with existing tunings
            combo = QComboBox()
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.NoInsert)
            combo.setMaxVisibleItems(15)
            combo.setStyleSheet(_COMBO_CELL_STYLE)
            combo.addItem("")
            combo.addItems(six_tunings)
            combo.setPlaceholderText("looking up…")
            self._review_table.setCellWidget(row, 2, combo)
            self._row_tuning_combos.append(combo)

            # 7-string checkbox — centred in cell
            chk_container = QWidget()
            chk_lay = QHBoxLayout(chk_container)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk = QCheckBox()
            chk.setStyleSheet("QCheckBox::indicator { width: 14px; height: 14px; }")
            chk_lay.addWidget(chk)
            # When 7-str toggled, swap the tuning options in the same row's combo
            chk.toggled.connect(
                lambda checked, c=combo, s6=six_tunings, s7=seven_tunings:
                    self._swap_tuning_options(c, checked, s6, s7)
            )
            self._review_table.setCellWidget(row, 3, chk_container)
            self._row_seven_checks.append(chk)

        self._review_table.resizeRowsToContents()

    def _swap_tuning_options(self, combo, is_seven, six_tunings, seven_tunings):
        current = combo.currentText()
        combo.clear()
        combo.addItem("")
        combo.addItems(seven_tunings if is_seven else six_tunings)
        if current in (seven_tunings if is_seven else six_tunings):
            combo.setCurrentText(current)

    def _start_tuning_lookups(self):
        n = self._review_table.rowCount()
        if n == 0:
            return
        self._set_busy(True, f"Looking up tunings from Ultimate Guitar… (0 / {n})")
        self._tuning_done_count = 0
        self._tuning_total      = n
        for row in range(n):
            title = self._review_table.item(row, 0).text()
            w = _TuningLookupWorker(row, self._artist_name, title)
            self._workers.append(w)
            w.done.connect(lambda r, t, s, _w=w: self._on_tuning_looked_up(_w, r, t, s))
            w.start()

    def _on_tuning_looked_up(self, worker, row, tuning, is_seven):
        self._remove_worker(worker)
        self._tuning_done_count += 1

        combo = self._row_tuning_combos[row] if row < len(self._row_tuning_combos) else None
        chk   = self._row_seven_checks[row]  if row < len(self._row_seven_checks)  else None

        if combo and tuning:
            # Insert the looked-up tuning at position 1 (after blank) if not already there
            all_items = [combo.itemText(i) for i in range(combo.count())]
            if tuning not in all_items:
                combo.insertItem(1, tuning)
            combo.setCurrentText(tuning)

        if chk and is_seven:
            chk.setChecked(True)

        remaining = self._tuning_total - self._tuning_done_count
        if remaining > 0:
            self._set_busy(
                True,
                f"Looking up tunings from Ultimate Guitar… "
                f"({self._tuning_done_count} / {self._tuning_total})",
            )
        else:
            found = sum(
                1 for c in self._row_tuning_combos if c.currentText().strip()
            )
            self._set_busy(
                False,
                f"UG lookup complete — {found} of {self._tuning_total} found. "
                f"Click a tuning cell to change it.",
            )

    # ------------------------------------------------------------------
    # Final step — collect and accept
    # ------------------------------------------------------------------
    def _collect_and_accept(self):
        rating = self._rating_widget.getRating()
        genre  = self._genre_combo.currentText().strip()

        self.result_tabs = []
        for row in range(self._review_table.rowCount()):
            title = self._review_table.item(row, 0).text()
            album = self._review_table.item(row, 1).text()

            combo    = self._row_tuning_combos[row] if row < len(self._row_tuning_combos) else None
            chk      = self._row_seven_checks[row]  if row < len(self._row_seven_checks)  else None
            tuning   = combo.currentText().strip() if combo else ""
            is_seven = chk.isChecked()             if chk   else False

            self.result_tabs.append({
                "band": self._artist_name, "album": album, "title": title,
                "tuning": tuning, "is_seven_string": is_seven,
                "rating": rating, "genre": genre, "notes": "",
            })

        if not self.result_tabs:
            self._status_lbl.setText("Nothing to add.")
            return

        self.accept()
