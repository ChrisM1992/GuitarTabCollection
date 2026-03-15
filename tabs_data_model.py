from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt5.QtGui import QColor
import webbrowser
import urllib.parse

NOTES_MAX_DISPLAY = 45   # chars shown in the cell before truncation


class TabsDataModel(QAbstractTableModel):
    searchTabRequested = pyqtSignal(str, str)

    def __init__(self, data=None, columns=None):
        super().__init__()
        self._data = data if data is not None else []
        self.columns = list(columns) if columns is not None else []
        if "Ultimate Guitar" not in self.columns:
            self.columns.append("Ultimate Guitar")

    def get_row(self, n):
        """Public accessor for a data row — avoids direct _data access by callers."""
        return self._data[n]

    # ------------------------------------------------------------------
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    # ------------------------------------------------------------------
    def _notes_col(self):
        """Return the model column index for 'Notes', or -1 if absent."""
        try:
            return self.columns.index("Notes")
        except ValueError:
            return -1

    # ------------------------------------------------------------------
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        col  = index.column()
        col_name = self.columns[col]

        # ── Ultimate Guitar virtual column ────────────────────────────
        if col_name == "Ultimate Guitar":
            if role == Qt.DisplayRole:
                return ""
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            return None

        row_data = self._data[index.row()]

        # Safety guard — if data tuple is shorter than expected, return None
        if col >= len(row_data):
            return None

        value = row_data[col]

        # ── DisplayRole ───────────────────────────────────────────────
        if role == Qt.DisplayRole:
            if col == 5:  # Rating
                try:
                    return "★" * int(value)
                except (ValueError, TypeError):
                    return ""
            notes_col = self._notes_col()
            if notes_col >= 0 and col == notes_col:
                text = str(value) if value else ""
                return (text[:NOTES_MAX_DISPLAY] + "…") if len(text) > NOTES_MAX_DISPLAY else text
            return str(value) if value is not None else ""

        # ── ToolTipRole — show full notes text ────────────────────────
        if role == Qt.ToolTipRole:
            notes_col = self._notes_col()
            if notes_col >= 0 and col == notes_col:
                return str(value) if value else ""
            return None

        # ── TextAlignmentRole ─────────────────────────────────────────
        if role == Qt.TextAlignmentRole:
            if col == 5:  # Rating
                return Qt.AlignCenter
            return None

        # ── ForegroundRole ────────────────────────────────────────────
        if role == Qt.ForegroundRole:
            if col == 5:  # Rating — gold stars
                return QColor("#FFD700")
            return None

        return None

    # ------------------------------------------------------------------
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
        return None

    # ------------------------------------------------------------------
    def flags(self, index):
        """
        Cells are selectable and enabled.
        ItemIsEditable is intentionally NOT set — this prevents Qt from
        opening a built-in inline editor on double-click.
        Custom editing is handled entirely by our delegate editorEvent()
        methods (StarRatingDelegate, UltimateGuitarDelegate).
        """
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        col_name = self.columns[index.column()]
        if col_name in ("Ultimate Guitar",):
            return Qt.ItemIsEnabled  # not selectable either
        return base
