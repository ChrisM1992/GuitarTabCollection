import sqlite3
import pandas as pd

class DatabaseManager:
    """Manager for SQLite database operations"""

    def __init__(self, db_path):
        """Initialize the database manager"""
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create bands table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bands (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        ''')

        # Create tabs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tabs (
            id INTEGER PRIMARY KEY,
            band_id INTEGER NOT NULL,
            album TEXT,
            title TEXT NOT NULL,
            tuning TEXT,
            rating INTEGER,
            genre TEXT,
            FOREIGN KEY (band_id) REFERENCES bands (id)
        )
        ''')

        conn.commit()
        conn.close()

    def get_all_bands(self):
        """Get all bands from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM bands ORDER BY name")
        bands = cursor.fetchall()

        conn.close()
        return bands

    def get_band_id(self, band_name):
        """Get band ID by name, create if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try to get existing band
        cursor.execute("SELECT id FROM bands WHERE name = ?", (band_name,))
        result = cursor.fetchone()

        if result:
            band_id = result[0]
        else:
            # Create new band
            cursor.execute("INSERT INTO bands (name) VALUES (?)", (band_name,))
            band_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return band_id

    def get_tabs_for_band(self, band_id):
        """Get all tabs for a specific band"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre
        FROM tabs t
        JOIN bands b ON t.band_id = b.id
        WHERE t.band_id = ?
        ORDER BY t.album, t.title
        ''', (band_id,))

        tabs = cursor.fetchall()

        conn.close()
        return tabs

    def get_all_tabs(self):
        """Get all tabs from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre
        FROM tabs t
        JOIN bands b ON t.band_id = b.id
        ORDER BY b.name, t.album, t.title
        ''')

        tabs = cursor.fetchall()

        conn.close()
        return tabs

    def add_tab(self, tab_data):
        """Add a new tab to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get or create band
            band_id = self.get_band_id(tab_data["band"])

            # Insert tab
            cursor.execute('''
            INSERT INTO tabs (band_id, album, title, tuning, rating, genre)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                band_id,
                tab_data["album"],
                tab_data["title"],
                tab_data["tuning"],
                tab_data["rating"],
                tab_data["genre"]
            ))

            conn.commit()
            tab_id = cursor.lastrowid

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

        return tab_id

    def update_tab(self, tab_id, tab_data):
        """Update an existing tab"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get or create band
            band_id = self.get_band_id(tab_data["band"])

            # Update tab
            cursor.execute('''
            UPDATE tabs
            SET band_id = ?, album = ?, title = ?, tuning = ?, rating = ?, genre = ?
            WHERE id = ?
            ''', (
                band_id,
                tab_data["album"],
                tab_data["title"],
                tab_data["tuning"],
                tab_data["rating"],
                tab_data["genre"],
                tab_id
            ))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_tab(self, tab_id):
        """Delete a tab from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM tabs WHERE id = ?", (tab_id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def import_from_excel(self, excel_path):
        """Import data from Excel file"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(excel_path)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Process each sheet (band)
            for sheet_name in excel_file.sheet_names:
                # Read sheet
                df = excel_file.parse(sheet_name)

                # Create or get band
                cursor.execute("SELECT id FROM bands WHERE name = ?", (sheet_name,))
                result = cursor.fetchone()

                if result:
                    band_id = result[0]
                else:
                    cursor.execute("INSERT INTO bands (name) VALUES (?)", (sheet_name,))
                    band_id = cursor.lastrowid

                # Process each row
                for _, row in df.iterrows():
                    # Extract data from row
                    try:
                        album = row.get('Album', '')
                        title = row.get('Title', '')
                        tuning = row.get('Tuning', '')
                        rating = row.get('Rating', 3)
                        genre = row.get('Genre', '')

                        # Insert tab
                        cursor.execute('''
                        INSERT INTO tabs (band_id, album, title, tuning, rating, genre)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (band_id, album, title, tuning, rating, genre))
                    except Exception as e:
                        print(f"Error importing row: {e}")
                        continue

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            print(f"Error importing Excel file: {e}")
            return False