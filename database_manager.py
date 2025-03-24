import sqlite3
import pandas as pd
from datetime import datetime


class DatabaseManager:
    """Manager for SQLite database operations"""

    def __init__(self, db_path):
        """Initialize the database manager"""
        self.db_path = db_path
        self.initialize_db()

    def migrate_tunings_table(self):
        """Migrate tunings table to add is_seven_string column"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if column exists
            cursor.execute("PRAGMA table_info(tunings)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]

            if 'is_seven_string' not in column_names:
                # Add the column with a default of 0
                cursor.execute("ALTER TABLE tunings ADD COLUMN is_seven_string INTEGER DEFAULT 0")
                conn.commit()
                print("Added is_seven_string column to tunings table")

        except sqlite3.OperationalError as e:
            print(f"Error migrating tunings table: {e}")
        finally:
            conn.close()

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

        # Create tunings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tunings (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            is_seven_string INTEGER DEFAULT 0
        )
        ''')
        
        # Create learned_tabs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learned_tabs (
            id INTEGER PRIMARY KEY,
            tab_id INTEGER NOT NULL,
            learned_date TEXT,
            FOREIGN KEY (tab_id) REFERENCES tabs (id)
        )
        ''')

        # Insert default tunings if they don't exist
        default_tunings = ["E A D G B E", "C G C F A D", "D G C F A D"]
        for tuning in default_tunings:
            cursor.execute("INSERT OR IGNORE INTO tunings (name, is_seven_string) VALUES (?, 0)", (tuning,))

        conn.commit()
        conn.close()

        # Call migration method
        self.migrate_tunings_table()

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

    def get_all_tunings(self, seven_string=False):
        """Get tunings, optionally filtering by 7-string"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if seven_string:
            cursor.execute("SELECT name FROM tunings WHERE is_seven_string = 1 ORDER BY name")
        else:
            cursor.execute("SELECT name FROM tunings WHERE is_seven_string = 0 ORDER BY name")
        
        tunings = [row[0] for row in cursor.fetchall()]

        conn.close()
        return tunings

    def add_tuning(self, tuning_name, is_seven_string=False):
        """Add a new tuning to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT OR IGNORE INTO tunings (name, is_seven_string) VALUES (?, ?)", 
                (tuning_name, 1 if is_seven_string else 0)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_tuning(self, tuning_name):
        """Delete a tuning from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if any tabs are using this tuning
            cursor.execute("SELECT COUNT(*) FROM tabs WHERE tuning = ?", (tuning_name,))
            tab_count = cursor.fetchone()[0]
            
            if tab_count > 0:
                # There are tabs using this tuning, we should not delete it
                conn.close()
                return False
                
            # Delete the tuning
            cursor.execute("DELETE FROM tunings WHERE name = ?", (tuning_name,))
            conn.commit()
            
            # Check if any rows were affected
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
            
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error deleting tuning: {str(e)}")
            return False

    def add_tab(self, tab_data):
        """Add a new tab to the database with duplicate checking"""
        # Check for duplicate before attempting to add
        if self.tab_exists(tab_data["band"], tab_data["album"], tab_data["title"]):
            raise ValueError(f"A tab for '{tab_data['title']}' by '{tab_data['band']}' from album '{tab_data['album']}' already exists")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get or create band
            band_id = self.get_band_id(tab_data["band"])

            # Update tuning table (if 7-string flag is present)
            is_seven_string = tab_data.get('is_seven_string', False)
            
            # First, check if tuning exists
            cursor.execute("SELECT id FROM tunings WHERE name = ?", (tab_data["tuning"],))
            tuning_result = cursor.fetchone()
            
            if not tuning_result:
                # If tuning doesn't exist, add it with 7-string flag
                cursor.execute(
                    "INSERT INTO tunings (name, is_seven_string) VALUES (?, ?)", 
                    (tab_data["tuning"], 1 if is_seven_string else 0)
                )

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

            # Update tuning table (if 7-string flag is present)
            is_seven_string = tab_data.get('is_seven_string', False)
            
            # First, check if tuning exists
            cursor.execute("SELECT id FROM tunings WHERE name = ?", (tab_data["tuning"],))
            tuning_result = cursor.fetchone()
            
            if not tuning_result:
                # If tuning doesn't exist, add it with 7-string flag
                cursor.execute(
                    "INSERT INTO tunings (name, is_seven_string) VALUES (?, ?)", 
                    (tab_data["tuning"], 1 if is_seven_string else 0)
                )

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
            # First delete any learned_tabs records
            cursor.execute("DELETE FROM learned_tabs WHERE tab_id = ?", (tab_id,))
            
            # Then delete the tab
            cursor.execute("DELETE FROM tabs WHERE id = ?", (tab_id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    

    def clean_up_empty_bands(self):
        """Remove bands that don't have any tabs associated with them"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Find bands with no tabs
            cursor.execute('''
            SELECT b.id, b.name FROM bands b
            LEFT JOIN tabs t ON b.id = t.band_id
            WHERE t.id IS NULL
            ''')
            
            empty_bands = cursor.fetchall()
            
            # Delete each empty band
            for band_id, band_name in empty_bands:
                cursor.execute("DELETE FROM bands WHERE id = ?", (band_id,))
            
            conn.commit()
            
            return len(empty_bands)  # Return number of bands deleted
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error cleaning up empty bands: {str(e)}")
            return 0  # Return 0 on error
        finally:
            if conn:
                conn.close()

    def add_to_learned(self, tab_id):
        """Add a tab to the learned tabs table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if tab is already in learned tabs
            cursor.execute("SELECT id FROM learned_tabs WHERE tab_id = ?", (tab_id,))
            if cursor.fetchone():
                conn.close()
                return False  # Already in learned tabs
            
            # Add to learned tabs with current date
            current_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                "INSERT INTO learned_tabs (tab_id, learned_date) VALUES (?, ?)",
                (tab_id, current_date)
            )
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def remove_from_learned(self, tab_id):
        """Remove a tab from the learned tabs table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM learned_tabs WHERE tab_id = ?", (tab_id,))
            conn.commit()
            conn.close()
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def get_all_learned_tabs(self):
        """Get all learned tabs from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre, lt.learned_date
        FROM tabs t
        JOIN bands b ON t.band_id = b.id
        JOIN learned_tabs lt ON t.id = lt.tab_id
        ORDER BY b.name, t.album, t.title
        ''')

        tabs = cursor.fetchall()
        conn.close()
        return tabs

    def is_tab_learned(self, tab_id):
        """Check if a tab is marked as learned"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM learned_tabs WHERE tab_id = ?", (tab_id,))
        result = cursor.fetchone() is not None
        
        conn.close()
        return result

    # Update the import_from_excel method in DatabaseManager class
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
                        album = row.get('Album Name', '')
                        title = row.get('Title', '')
                        tuning = row.get('Tuning', '')
                        rating = row.get('Rating', 1)
                        genre = row.get('Genre', '')
                        
                        # Determine if 7-string (new column or inference)
                        is_seven_string = row.get('Is7String', False)
                        
                        # Check if tuning exists in tunings table
                        cursor.execute(
                            "SELECT id FROM tunings WHERE name = ?", 
                            (tuning,)
                        )
                        tuning_result = cursor.fetchone()
                        
                        # If tuning doesn't exist, add it
                        if not tuning_result:
                            cursor.execute(
                                "INSERT INTO tunings (name, is_seven_string) VALUES (?, ?)", 
                                (tuning, 1 if is_seven_string else 0)
                            )

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

    def tab_exists(self, band_name, album, title):
        """Check if a tab with the same band, album and title already exists
        
        Args:
            band_name (str): Name of the band
            album (str): Album name
            title (str): Song title
            
        Returns:
            bool: True if the tab already exists, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get band_id for the given band_name
            cursor.execute("SELECT id FROM bands WHERE name = ?", (band_name,))
            band_result = cursor.fetchone()
            
            if not band_result:
                # If band doesn't exist, then tab doesn't exist
                return False
                
            band_id = band_result[0]
            
            # Check if a tab with the same band_id, album and title exists
            cursor.execute("""
            SELECT COUNT(*) FROM tabs 
            WHERE band_id = ? AND album = ? AND title = ?
            """, (band_id, album, title))
            
            count = cursor.fetchone()[0]
            return count > 0
            
        except Exception as e:
            print(f"Error checking for duplicate tab: {str(e)}")
            return False
        finally:
            conn.close()