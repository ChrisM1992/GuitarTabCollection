"""
Spotify 'Now Playing' client — nur Python-Stdlib, kein requests/spotipy.
Spotify-App-Registrierung: https://developer.spotify.com/dashboard
Redirect URI muss dort eingetragen werden: http://localhost:8765/callback
"""
import base64
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

_AUTH_URL    = "https://accounts.spotify.com/authorize"
_TOKEN_URL   = "https://accounts.spotify.com/api/token"
_NOW_PLAYING = "https://api.spotify.com/v1/me/player/currently-playing"
_REDIRECT    = "http://127.0.0.1:8765/callback"
_SCOPE       = "user-read-currently-playing"
_POLL_MS     = 5000


class SpotifyClient(QObject):
    """Emittiert track_changed / track_stopped auf dem Qt-Haupt-Thread via Signals."""

    track_changed = pyqtSignal(str, str)  # (artist, title)
    track_stopped = pyqtSignal()
    auth_success  = pyqtSignal()
    auth_error    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client_id     = ""
        self._client_secret = ""
        self._access_token  = ""
        self._refresh_token = ""
        self._current_key   = None  # (artist, title) — erkennt Titelwechsel

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

    # ── Konfiguration ────────────────────────────────────────────────────

    def configure(self, client_id: str, client_secret: str):
        self._client_id     = client_id.strip()
        self._client_secret = client_secret.strip()

    def set_refresh_token(self, token: str):
        self._refresh_token = token

    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def is_authenticated(self) -> bool:
        return bool(self._refresh_token)

    # ── OAuth-Flow ───────────────────────────────────────────────────────

    def start_auth(self):
        """Browser öffnen und Redirect-Code via lokalem HTTP-Server abfangen."""
        if not self.is_configured():
            self.auth_error.emit("Client-ID und Secret sind nicht konfiguriert.")
            return
        params = {
            "client_id":     self._client_id,
            "response_type": "code",
            "redirect_uri":  _REDIRECT,
            "scope":         _SCOPE,
        }
        webbrowser.open(_AUTH_URL + "?" + urllib.parse.urlencode(params))
        threading.Thread(target=self._capture_redirect, daemon=True).start()

    def _capture_redirect(self):
        holder = {}

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(inner_self):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(inner_self.path).query)
                holder["code"] = qs.get("code", [None])[0]
                inner_self.send_response(200)
                inner_self.send_header("Content-Type", "text/html; charset=utf-8")
                inner_self.end_headers()
                inner_self.wfile.write(
                    b"<html><body style='font-family:sans-serif;background:#121212;color:#fff;"
                    b"display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
                    b"<div style='text-align:center'>"
                    b"<h2 style='color:#1db954'>&#10003; Verbunden!</h2>"
                    b"<p>Du kannst dieses Tab schlie&szlig;en und zu GuitarTabs zur&uuml;ckkehren.</p>"
                    b"</div></body></html>"
                )

            def log_message(self, *_):
                pass

        try:
            srv = HTTPServer(("localhost", 8765), _Handler)
            srv.timeout = 120
            srv.handle_request()
            srv.server_close()
        except Exception as exc:
            self.auth_error.emit(f"Lokaler Callback-Server: {exc}")
            return

        code = holder.get("code")
        if not code:
            self.auth_error.emit("Kein Authorization-Code erhalten.")
            return

        self._exchange_code(code)

    def _exchange_code(self, code: str):
        data = urllib.parse.urlencode({
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": _REDIRECT,
        }).encode()
        try:
            body = self._token_request(data)
        except Exception as exc:
            self.auth_error.emit(f"Token-Austausch fehlgeschlagen: {exc}")
            return
        self._access_token  = body.get("access_token", "")
        self._refresh_token = body.get("refresh_token", "")
        self.auth_success.emit()
        self.start_polling()

    def _refresh_access_token(self) -> bool:
        if not self._refresh_token:
            return False
        data = urllib.parse.urlencode({
            "grant_type":    "refresh_token",
            "refresh_token": self._refresh_token,
        }).encode()
        try:
            body = self._token_request(data)
            self._access_token = body.get("access_token", "")
            return bool(self._access_token)
        except Exception:
            return False

    def _token_request(self, data: bytes) -> dict:
        creds = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        req = urllib.request.Request(_TOKEN_URL, data=data, headers={
            "Authorization": f"Basic {creds}",
            "Content-Type":  "application/x-www-form-urlencoded",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    # ── Polling ──────────────────────────────────────────────────────────

    def start_polling(self):
        if not self._poll_timer.isActive():
            self._poll()
            self._poll_timer.start()

    def stop_polling(self):
        self._poll_timer.stop()
        self._current_key = None

    def disconnect_account(self):
        self.stop_polling()
        self._access_token  = ""
        self._refresh_token = ""
        self._current_key   = None

    def _poll(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        if not self._access_token:
            if not self._refresh_access_token():
                return

        req = urllib.request.Request(_NOW_PLAYING, headers={
            "Authorization": f"Bearer {self._access_token}",
        })
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                if r.status == 204:
                    self._maybe_stop()
                    return
                body = json.loads(r.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and self._refresh_access_token():
                self._fetch()
            return
        except Exception:
            return

        if not body or not body.get("is_playing"):
            self._maybe_stop()
            return

        item    = body.get("item") or {}
        title   = item.get("name", "")
        artists = item.get("artists") or []
        artist  = artists[0]["name"] if artists else ""
        key     = (artist, title)
        if key != self._current_key:
            self._current_key = key
            self.track_changed.emit(artist, title)  # Qt queued cross-thread

    def _maybe_stop(self):
        if self._current_key is not None:
            self._current_key = None
            self.track_stopped.emit()
