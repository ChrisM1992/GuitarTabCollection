from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QTableWidget, QTableWidgetItem, QComboBox, QSpinBox)

class BatchAddDialog(QDialog):
    def __init__(self, bands, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Add Tabs")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # Create layout
        layout = QVBoxLayout(self)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Band', 'Album', 'Title', 'Tuning', 'Rating', 'Genre'])
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self.add_row)
        remove_row_btn = QPushButton("Remove Row")
        remove_row_btn.clicked.connect(self.remove_row)
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(add_row_btn)
        button_layout.addWidget(remove_row_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.bands = bands
        self.add_row()  # Add first row by default

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Add band combo box
        band_combo = QComboBox()
        band_combo.addItems(self.bands)
        self.table.setCellWidget(row, 0, band_combo)

        # Add rating spin box
        rating_spin = QSpinBox()
        rating_spin.setRange(1, 5)
        self.table.setCellWidget(row, 4, rating_spin)

        # Add empty items for other columns
        for col in [1, 2, 3, 5]:
            self.table.setItem(row, col, QTableWidgetItem(""))

    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def getTabsData(self):
        tabs = []
        for row in range(self.table.rowCount()):
            band = self.table.cellWidget(row, 0).currentText()
            album = self.table.item(row, 1).text()
            title = self.table.item(row, 2).text()
            tuning = self.table.item(row, 3).text()
            rating = self.table.cellWidget(row, 4).value()
            genre = self.table.item(row, 5).text()
            
            if band and album and title:  # Only add if required fields are filled
                tabs.append({
                    'band': band,
                    'album': album,
                    'title': title,
                    'tuning': tuning,
                    'rating': rating,
                    'genre': genre
                })
        return tabs