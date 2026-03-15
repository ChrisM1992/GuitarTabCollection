import ssl
import json
import urllib.request
import urllib.parse

from PyQt5.QtCore import QThread, pyqtSignal, QObject

# Apple iTunes Search API — free, public, no API key required.
# Docs: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
_ITUNES_URL = "https://itunes.apple.com/search"


class _SuggestWorker(QThread):
    finished = pyqtSignal(str, str, int, object)  # band, title, tab_id, dict

    def __init__(self, band, title, tab_id, mode="full", parent=None):
        super().__init__(parent)
        self.band   = band
        self.title  = title
        self.tab_id = tab_id
        self.mode   = mode

    def run(self):
        try:
            results = self._fetch()
        except Exception:
            results = {}
        self.finished.emit(self.band, self.title, self.tab_id, results)

    def _fetch(self):
        if self.mode == "tuning":
            return {}  # iTunes has no tuning data

        params = urllib.parse.urlencode({
            'term':   f"{self.band} {self.title}",
            'entity': 'song',
            'limit':  '10',
        })
        url = f"{_ITUNES_URL}?{params}"

        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={
            'User-Agent': 'GuitarTabCollection/1.0',
        })
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        return self._extract(data.get('results', []))

    # ------------------------------------------------------------------
    def _extract(self, results):
        if not results:
            return {}

        band_lower  = self.band.lower().strip()
        title_lower = self.title.lower().strip()

        # ── Find the best matching track ──────────────────────────────
        # Pass 1: exact artist + title match, prefer Album over Single
        # Pass 2: exact artist match, any title variant
        # Pass 3: first result regardless of artist

        def _is_album(r):
            return r.get('collectionType', '').lower() == 'album'

        candidates = [r for r in results
                      if r.get('artistName', '').lower() == band_lower]

        # Among artist-matching candidates, prefer studio albums
        exact_title = [r for r in candidates
                       if r.get('trackName', '').lower() == title_lower]

        best = None
        for pool in (
            [r for r in exact_title if _is_album(r)],   # exact + album
            exact_title,                                  # exact, any release
            [r for r in candidates if _is_album(r)],     # same artist + album
            candidates,                                   # same artist, anything
            results,                                      # fallback
        ):
            if pool:
                best = pool[0]
                break

        if best is None:
            return {}

        out = {}

        # Suggest corrected track title capitalisation
        itunes_title = best.get('trackName', '').strip()
        if itunes_title and itunes_title.lower() != title_lower:
            out['title'] = itunes_title

        # Suggest corrected artist capitalisation
        itunes_artist = best.get('artistName', '').strip()
        if itunes_artist and itunes_artist.lower() != band_lower:
            out['band'] = itunes_artist

        # Album name (only when mode requests it)
        if self.mode in ('full', 'album'):
            album = best.get('collectionName', '').strip()
            if album:
                out['album'] = album

        return out


# ---------------------------------------------------------------------------
class TitleChecker(QObject):
    """Manages _SuggestWorker threads — keeps refs alive, cleans up on finish."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []

    def check(self, band, title, tab_id, mode, callback):
        """Fire a background iTunes lookup.
        callback(band, title, tab_id, dict) is called on the main thread."""
        worker = _SuggestWorker(band, title, tab_id, mode)
        self._workers.append(worker)
        worker.finished.connect(
            lambda b, t, tid, d: self._on_done(worker, b, t, tid, d, callback)
        )
        worker.start()

    def _on_done(self, worker, band, title, tab_id, data, callback):
        try:
            callback(band, title, tab_id, data)
        finally:
            try:
                self._workers.remove(worker)
            except ValueError:
                pass
