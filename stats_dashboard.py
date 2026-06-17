"""
Statistics Dashboard  —  "My Guitar Stats"
Visual overview: collection KPI cards, custom bar charts, and a
personalised "Guitar Story" summary card.
"""
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea,
    QWidget, QLabel, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QBrush, QFontMetrics


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_AMBER  = QColor("#e3ac63")
_GREEN  = QColor("#7bc67e")
_BLUE   = QColor("#6a9fd8")

_CHART_COLORS = [
    QColor("#e3ac63"), QColor("#6a9fd8"), QColor("#7bc67e"),
    QColor("#d67ec6"), QColor("#e07b7b"), QColor("#7bd6c6"),
    QColor("#d6c67b"), QColor("#9b7bd6"), QColor("#d6937b"),
    QColor("#7b9bd6"),
]

# Colour ramp per star count (0 = unrated, grey; 1-5 = red → green)
_STAR_COLORS = [
    QColor("#444448"),  # 0 unrated
    QColor("#e07b7b"),  # 1 ★
    QColor("#d6937b"),  # 2 ★★
    QColor("#d6c67b"),  # 3 ★★★
    QColor("#a8d67b"),  # 4 ★★★★
    QColor("#7bc67e"),  # 5 ★★★★★
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #e3ac63; font-size: 10px; font-weight: bold; "
        "letter-spacing: 2px; background: transparent; border: none;"
    )
    return lbl


def _hr() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #2a2a30; max-height: 1px;")
    return line


def _card_frame() -> QFrame:
    f = QFrame()
    f.setStyleSheet(
        "QFrame { background: #252528; border: 1px solid #3a3a42;"
        " border-radius: 8px; }"
    )
    return f


# ---------------------------------------------------------------------------
# KPI card
# ---------------------------------------------------------------------------
class _StatCard(QFrame):
    """One big number with a small label underneath."""

    def __init__(self, value, label: str, color: str = "#e3ac63", parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setMinimumWidth(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "QFrame { background: #252528; border: 1px solid #3a3a42;"
            " border-radius: 8px; }"
            "QLabel { background: transparent; border: none; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignCenter)

        val_lbl = QLabel(str(value))
        val_lbl.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(22)
        f.setBold(True)
        val_lbl.setFont(f)
        val_lbl.setStyleSheet(f"color: {color};")
        lay.addWidget(val_lbl)

        sub_lbl = QLabel(label)
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet(
            "color: #666669; font-size: 9px; letter-spacing: 1px;"
        )
        lay.addWidget(sub_lbl)


# ---------------------------------------------------------------------------
# Horizontal bar chart
# ---------------------------------------------------------------------------
class _HBarChart(QWidget):
    """
    Horizontal bar chart.
    data: list of (str label, int value), largest-first order assumed.
    multi_color: each bar gets a different colour from _CHART_COLORS.
    """

    _LABEL_W = 175
    _VAL_W   = 46
    _ROW_H   = 34
    _PAD_V   = 8

    def __init__(self, data: list, multi_color: bool = False, parent=None):
        super().__init__(parent)
        self._data  = data or []
        self._multi = multi_color
        h = len(self._data) * self._ROW_H + self._PAD_V * 2
        self.setFixedHeight(max(50, h))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W       = self.width()
        bar_area = max(10, W - self._LABEL_W - self._VAL_W - 8)
        max_val  = max(v for _, v in self._data) or 1

        f_label = QFont()
        f_label.setPointSize(10)
        f_val = QFont()
        f_val.setPointSize(9)
        fm = QFontMetrics(f_label)

        for i, (label, val) in enumerate(self._data):
            cy    = self._PAD_V + i * self._ROW_H + self._ROW_H // 2
            bar_h = 18
            bar_y = cy - bar_h // 2

            # label (right-aligned, elided if too long)
            p.setFont(f_label)
            p.setPen(QColor("#bbbbbb"))
            elided = fm.elidedText(label, Qt.ElideRight, self._LABEL_W - 10)
            p.drawText(
                QRectF(0, bar_y, self._LABEL_W - 8, bar_h),
                Qt.AlignVCenter | Qt.AlignRight, elided,
            )

            # bar
            bw  = max(6, int(val / max_val * bar_area))
            bx  = float(self._LABEL_W)
            col = _CHART_COLORS[i % len(_CHART_COLORS)] if self._multi else _AMBER
            p.setBrush(QBrush(col))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(bx, bar_y, bw, bar_h), 4, 4)

            # value to the right of the bar
            p.setFont(f_val)
            p.setPen(QColor("#888888"))
            p.drawText(
                QRectF(bx + bw + 6, bar_y, float(self._VAL_W - 6), bar_h),
                Qt.AlignVCenter | Qt.AlignLeft, str(val),
            )

        p.end()


# ---------------------------------------------------------------------------
# Vertical bar chart
# ---------------------------------------------------------------------------
class _VBarChart(QWidget):
    """
    Vertical bar chart.
    data:   list of (str label, int value).
    colors: optional list of QColor per bar; falls back to amber.
    """

    _PAD_L = 28
    _PAD_R = 10
    _PAD_T = 22
    _PAD_B = 38

    def __init__(self, data: list, colors: list = None, parent=None):
        super().__init__(parent)
        self._data   = data or []
        self._colors = colors
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, _):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H    = self.width(), self.height()
        cw      = W - self._PAD_L - self._PAD_R
        ch      = H - self._PAD_T - self._PAD_B
        n       = len(self._data)
        max_val = max(v for _, v in self._data) or 1
        slot_w  = cw / n
        bar_w   = max(6.0, slot_w * 0.55)

        f_val   = QFont(); f_val.setPointSize(8)
        f_label = QFont(); f_label.setPointSize(8)
        many    = n > 8          # rotate labels when crowded

        for i, (label, val) in enumerate(self._data):
            cx = self._PAD_L + i * slot_w + slot_w / 2
            bx = cx - bar_w / 2
            bh = int(val / max_val * ch) if max_val else 0
            by = self._PAD_T + ch - bh

            col = (self._colors[i] if self._colors and i < len(self._colors)
                   else _AMBER)
            p.setBrush(QBrush(col))
            p.setPen(Qt.NoPen)
            if bh > 0:
                p.drawRoundedRect(QRectF(bx, by, bar_w, bh), 3, 3)

            # value above bar
            if val > 0:
                p.setFont(f_val)
                p.setPen(QColor("#aaaaaa"))
                p.drawText(QRectF(cx - 20, by - 18, 40, 16), Qt.AlignCenter, str(val))

            # label below
            p.setFont(f_label)
            p.setPen(QColor("#777777"))
            if many:
                p.save()
                p.translate(cx, H - self._PAD_B + 5)
                p.rotate(-40)
                p.drawText(QRectF(-24, 0, 48, 14), Qt.AlignLeft | Qt.AlignVCenter, label)
                p.restore()
            else:
                p.drawText(
                    QRectF(cx - slot_w / 2, H - self._PAD_B + 4, slot_w, self._PAD_B - 4),
                    Qt.AlignTop | Qt.AlignHCenter, label,
                )

        p.end()


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------
class StatsDashboard(QDialog):

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Guitar Stats")
        self.setMinimumSize(820, 660)
        self.resize(980, 820)
        self._db = db_manager
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── header bar ──────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet(
            "QFrame { background: #17171b; border-bottom: 1px solid #2a2a30; }"
            "QLabel { background: transparent; border: none; }"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        title = QLabel("My Guitar Stats")
        tf = QFont(); tf.setPointSize(14); tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color: #e3ac63;")
        hl.addWidget(title)
        hl.addStretch()

        yr = QLabel(str(datetime.now().year))
        yr.setStyleSheet(
            "color: #2e2e34; font-size: 22px; font-weight: bold;"
        )
        hl.addWidget(yr)
        outer.addWidget(header)

        # ── scrollable body ──────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        body = QWidget()
        body.setStyleSheet("background: #1e1e22;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 28)
        lay.setSpacing(14)

        stats = self._db.get_stats()
        if stats['total_tabs'] == 0:
            self._build_empty(lay)
        else:
            self._build_content(lay, stats)

        lay.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # ------------------------------------------------------------------
    def _build_empty(self, lay):
        lay.addStretch()
        lbl = QLabel(
            "No tabs in your collection yet.\n"
            "Add some tabs to see your stats here."
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #444448; font-size: 14px;")
        lay.addWidget(lbl)
        lay.addStretch()

    # ------------------------------------------------------------------
    def _build_content(self, lay, s):
        total   = s['total_tabs']
        learned = s['total_learned']
        pct     = int(learned / total * 100) if total else 0

        # ── KPI cards ──────────────────────────────────────
        lay.addWidget(_section_label("OVERVIEW"))
        lay.addWidget(_hr())
        cards = QHBoxLayout()
        cards.setSpacing(10)
        cards.addWidget(_StatCard(total,             "TOTAL TABS"))
        cards.addWidget(_StatCard(learned,           "LEARNED",    color="#7bc67e"))
        cards.addWidget(_StatCard(f"{pct}%",         "COMPLETION", color="#6a9fd8"))
        cards.addWidget(_StatCard(s['total_bands'],  "BANDS"))
        cards.addWidget(_StatCard(s['total_genres'], "GENRES",     color="#d67ec6"))
        lay.addLayout(cards)

        # ── Rating distribution ─────────────────────────────
        lay.addSpacing(4)
        lay.addWidget(_section_label("RATING DISTRIBUTION"))
        lay.addWidget(_hr())
        rating_data   = []
        rating_colors = []
        for star in range(1, 6):
            rating_data.append(("★" * star, s['ratings'].get(str(star), 0)))
            rating_colors.append(_STAR_COLORS[star])
        f = _card_frame()
        f.setFixedHeight(190)
        fl = QVBoxLayout(f)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.addWidget(_VBarChart(rating_data, colors=rating_colors))
        lay.addWidget(f)

        # ── Top bands ──────────────────────────────────────
        if s['top_bands']:
            lay.addSpacing(4)
            lay.addWidget(_section_label("TOP BANDS BY TAB COUNT"))
            lay.addWidget(_hr())
            f = _card_frame()
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 12, 16, 12)
            fl.addWidget(_HBarChart(s['top_bands'], multi_color=True))
            lay.addWidget(f)

        # ── Genre breakdown ─────────────────────────────────
        if s['genres']:
            lay.addSpacing(4)
            lay.addWidget(_section_label("GENRE BREAKDOWN"))
            lay.addWidget(_hr())
            f = _card_frame()
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 12, 16, 12)
            fl.addWidget(_HBarChart(s['genres'], multi_color=True))
            lay.addWidget(f)

        # ── Tuning usage ────────────────────────────────────
        if s['tunings']:
            lay.addSpacing(4)
            lay.addWidget(_section_label("TUNING USAGE"))
            lay.addWidget(_hr())
            f = _card_frame()
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 12, 16, 12)
            fl.addWidget(_HBarChart(s['tunings'], multi_color=False))
            lay.addWidget(f)

        # ── Songs learned per month ─────────────────────────
        if s['learned_by_month']:
            lay.addSpacing(4)
            lay.addWidget(_section_label("SONGS LEARNED PER MONTH"))
            lay.addWidget(_hr())
            span_years = len(s['learned_by_month']) > 12
            month_data = []
            for ym, cnt in s['learned_by_month']:
                try:
                    d = datetime.strptime(ym, "%Y-%m")
                    lbl = d.strftime("%b '%y") if span_years else d.strftime("%b")
                except Exception:
                    lbl = ym
                month_data.append((lbl, cnt))
            f = _card_frame()
            f.setFixedHeight(220)
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 10, 16, 10)
            fl.addWidget(_VBarChart(month_data, colors=[_GREEN] * len(month_data)))
            lay.addWidget(f)

        # ── Guitar Story ────────────────────────────────────
        lay.addSpacing(4)
        lay.addWidget(_section_label("YOUR GUITAR STORY"))
        lay.addWidget(_hr())
        lay.addWidget(self._story_card(s))

    # ------------------------------------------------------------------
    def _story_card(self, s) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background: #1a2a1a; border: 1px solid #3a5a3a;"
            " border-radius: 8px; }"
            "QLabel { background: transparent; border: none; }"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(22, 16, 22, 18)
        lay.setSpacing(8)

        for line in self._story_lines(s):
            lbl = QLabel(line)
            lbl.setWordWrap(True)
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("color: #b0d8b0; font-size: 12px;")
            lay.addWidget(lbl)

        return f

    def _story_lines(self, s) -> list:
        total   = s['total_tabs']
        learned = s['total_learned']
        pct     = int(learned / total * 100) if total else 0

        def hi(v):
            return (f'<span style="color:#e3ac63; font-weight:bold;">'
                    f'{v}</span>')

        lines = []

        lines.append(
            f"Your collection holds {hi(total)} tabs across {hi(s['total_bands'])} bands."
        )

        if learned:
            lines.append(
                f"You've learned {hi(learned)} of them — "
                f"that's {hi(f'{pct}%')} of your library."
            )
        else:
            lines.append(
                "You haven't marked any tabs as learned yet. "
                "Right-click a song in your collection to start!"
            )

        if s['top_bands']:
            b = s['top_bands'][0]
            lines.append(
                f"Your most collected band is {hi(b[0])} "
                f"with {hi(b[1])} tabs."
            )

        if s['genres']:
            g = s['genres'][0]
            lines.append(
                f"Your dominant genre is {hi(g[0])} ({hi(g[1])} tabs)."
            )

        if s['tunings']:
            t = s['tunings'][0]
            lines.append(
                f"Your favourite tuning is {hi(t[0])}, "
                f"used on {hi(t[1])} song(s)."
            )

        if s['learned_by_month']:
            best = max(s['learned_by_month'], key=lambda x: x[1])
            try:
                month_str = datetime.strptime(best[0], "%Y-%m").strftime("%B %Y")
            except Exception:
                month_str = best[0]
            lines.append(
                f"Your most productive learning month was {hi(month_str)} "
                f"— {hi(best[1])} song(s) learned."
            )

        rated    = sum(s['ratings'].get(str(i), 0) for i in range(1, 6))
        unrated  = total - rated
        if unrated:
            lines.append(
                f"You still have {hi(unrated)} unrated tab(s) "
                f"— worth giving them a star."
            )
        if rated:
            avg = sum(i * s['ratings'].get(str(i), 0)
                      for i in range(1, 6)) / rated
            lines.append(
                f"Your average rating is {hi(f'{avg:.1f}')} across rated tabs."
            )

        if pct == 0:
            lines.append("Your library is waiting — let's start learning!")
        elif pct < 25:
            lines.append("Great start — keep adding and learning.")
        elif pct < 50:
            lines.append("You're making solid progress through your collection.")
        elif pct < 75:
            lines.append("Halfway there — your collection tells quite a story!")
        else:
            lines.append(
                "Outstanding — you've mastered most of your collection. Keep going!"
            )

        return lines
