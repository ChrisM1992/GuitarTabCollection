from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt5.QtGui import QColor

class TabsDataModel(QAbstractTableModel):
    """Data model for representing the guitar tabs collection"""

    def __init__(self, data=None, columns=None):
        super().__init__()
        self._data = data if data is not None else []
        self.columns = columns if columns is not None else []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            # Return the value from the data list
            value = self._data[index.row()][index.column()]

            # Format rating as stars
            if index.column() == 5:  # Rating column
                return "★" * int(value)

            # Handle different data types appropriately
            if isinstance(value, (float, int)):
                return str(value)
            return str(value)

        if role == Qt.BackgroundRole:
            # Remove custom background coloring to let stylesheet handle it
            return None

        if role == Qt.TextAlignmentRole:
            # Center align the rating column
            if index.column() == 5:  # Rating column
                return Qt.AlignCenter

        if role == Qt.ForegroundRole:
            # Make stars yellow/gold
            if index.column() == 5:  # Rating column
                return QColor("#FFD700")  # Gold color

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            row = index.row()
            column = index.column()

            # Create a new row list with the updated value
            new_row = list(self._data[row])
            
            # Special handling for rating column
            if column == 5:  # Rating column
                try:
                    # Try to convert value to int
                    if isinstance(value, str):
                        # If it's stars, count them
                        if "★" in value:
                            value = value.count("★")
                        else:
                            # Otherwise try to convert to int
                            value = int(value)
                    elif isinstance(value, (int, float)):
                        value = int(value)
                    
                    # Ensure rating is within valid range
                    value = max(1, min(5, value))
                except (ValueError, TypeError):
                    # If conversion fails, keep the old value
                    value = new_row[column]
            
            new_row[column] = value
            
            # Replace the old row with the new one
            self._data[row] = tuple(new_row)

            # Emit the dataChanged signal
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        # Make cells editable
        return super().flags(index) | Qt.ItemIsEditable

    def addRow(self, row_data):
        # Add new row to the model
        self.beginInsertRows(Qt.QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(tuple(row_data))
        self.endInsertRows()
        return True

    def removeRow(self, row, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        del self._data[row]
        self.endRemoveRows()
        return True

    def getAllData(self):
        # Return all data
        return self._data