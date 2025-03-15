# First, we'll modify the TabsDataModel class in tabs_data_model.py to support the new button column

# Add these imports to the top of tabs_data_model.py
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt5.QtGui import QColor
import webbrowser
import urllib.parse

# Modify the TabsDataModel class to include the search feature
class TabsDataModel(QAbstractTableModel):
    searchTabRequested = pyqtSignal(str, str)  # Signal for band and title
    
    def __init__(self, data=None, columns=None):
        super().__init__()
        self._data = data if data is not None else []
        self.columns = columns if columns is not None else []
        # Add "Ultimate Guitar" column if not already present
        if "Ultimate Guitar" not in self.columns:
            self.columns.append("Ultimate Guitar")

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        # Display role - what is shown in the cell
        if role == Qt.DisplayRole:
            # For the Search Tab column, return empty string (button is rendered separately)
            if self.columns[index.column()] == "Ultimate Guitar":
                return ""
                
            # Return the value from the data list
            value = self._data[index.row()][index.column()]

            # Format rating as stars
            if index.column() == 5:  # Rating column
                return "★" * int(value)

            # Handle different data types appropriately
            if isinstance(value, (float, int)):
                return str(value)
            return str(value)

        # Background role - cell background color
        if role == Qt.BackgroundRole:
            # Remove custom background coloring to let stylesheet handle it
            return None

        # Text alignment role
        if role == Qt.TextAlignmentRole:
            # Center align the rating column
            if index.column() == 5:  # Rating column
                return Qt.AlignCenter
                
            # Center align the Search Tab column
            if self.columns[index.column()] == "Ultimate Guitar":
                return Qt.AlignCenter

        # Foreground role - text color
        if role == Qt.ForegroundRole:
            # Make stars yellow/gold
            if index.column() == 5:  # Rating column
                return QColor("#FFD700")  # Gold color

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
        return None

    def flags(self, index):
        # Make all cells except "Ultimate Guitar" editable
        if self.columns[index.column()] == "Ultimate Guitar":
            return super().flags(index) | Qt.ItemIsEnabled
        else:
            return super().flags(index) | Qt.ItemIsEditable

    # Other methods remain the same...

# Now modify guitar_tabs_app.py to handle the search button functionality

# Add this method to the GuitarTabsApp class
def setupSearchTabButtons(self):
    """Setup the button delegate for the Search Tab column"""
    # For each table view in the tabs widget
    for i in range(self.tabs_widget.count()):
        tab_widget = self.tabs_widget.widget(i)
        if isinstance(tab_widget, QTableView):
            proxy_model = tab_widget.model()
            source_model = proxy_model.sourceModel()
            
            # Connect signal from model to handler
            source_model.searchTabRequested.connect(self.searchTabOnline)
            
            # Add button delegate to the Search Tab column
            from PyQt5.QtWidgets import QStyledItemDelegate, QPushButton
            
            class ButtonDelegate(QStyledItemDelegate):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    
                def createEditor(self, parent, option, index):
                    # Create a button for editing the cell
                    button = QPushButton("Search", parent)
                    button.clicked.connect(lambda: self.commitAndCloseEditor(button, index))
                    return button
                    
                def commitAndCloseEditor(self, editor, index):
                    # Commit data and close editor
                    proxy_model = index.model()
                    source_model = proxy_model.sourceModel()
                    source_index = proxy_model.mapToSource(index)
                    
                    # Get band and title data
                    source_row = source_index.row()
                    band = source_model._data[source_row][1]  # Band column (index 1)
                    title = source_model._data[source_row][3]  # Title column (index 3)
                    
                    # Emit signal to search
                    source_model.searchTabRequested.emit(band, title)
                    
                    # Close the editor
                    self.closeEditor.emit(editor)
                    
                def paint(self, painter, option, index):
                    # Only draw "Search" button if cell is not being edited
                    if not self.parent().indexWidget(index):
                        # Draw a button-like appearance
                        from PyQt5.QtWidgets import QStyle, QApplication
                        from PyQt5.QtCore import QRect
                        
                        button_option = QStyleOptionButton()
                        button_option.rect = option.rect
                        button_option.text = "🔍"  # Search icon
                        button_option.state = QStyle.State_Enabled
                        
                        QApplication.style().drawControl(
                            QStyle.CE_PushButton, button_option, painter)
                    
            # Get the Search Tab column index
            search_col_idx = source_model.columns.index("Ultimate Guitar")
            
            # Set the delegate for the column
            tab_widget.setItemDelegateForColumn(
                search_col_idx, ButtonDelegate(tab_widget))
            
            # Make the column a reasonable width
            tab_widget.setColumnWidth(search_col_idx, 80)

def searchTabOnline(self, band, title):
    """Search for a guitar tab online"""
    try:
        # Construct the search query without "guitar tab"
        query = f"{band} {title}"
        encoded_query = urllib.parse.quote(query)
        
        # Construct the Ultimate Guitar search URL
        url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={encoded_query}"
        
        # Open in default browser
        webbrowser.open(url)
        
        # Update status bar
        self.statusBar().showMessage(f"Searching for '{band} - {title}' on Ultimate Guitar...")
    except Exception as e:
        self.statusBar().showMessage(f"Error searching for tab: {str(e)}")

# Call setupSearchTabButtons after loading data
def load_data(self):
    """Load data from the database"""
    # ... existing load_data code ...
    
    # After all tables are created, setup the search buttons
    self.setupSearchTabButtons()
    
    # ... rest of the load_data method ...