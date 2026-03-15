import sqlite3
from datetime import datetime


class DatabaseManager:

    def __init__(self, db_path):
        self.db_path = db_path
        self.initialize_db()

    # ------------------------------------------------------------------
    # Schema setup & migrations
    # ------------------------------------------------------------------
    def initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bands (
                id   INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tabs (
                id      INTEGER PRIMARY KEY,
                band_id INTEGER NOT NULL,
                album   TEXT,
                title   TEXT NOT NULL,
                tuning  TEXT,
                rating  INTEGER,
                genre   TEXT,
                notes   TEXT DEFAULT '',
                FOREIGN KEY (band_id) REFERENCES bands (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tunings (
                id             INTEGER PRIMARY KEY,
                name           TEXT UNIQUE NOT NULL,
                is_seven_string INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_tabs (
                id           INTEGER PRIMARY KEY,
                tab_id       INTEGER NOT NULL,
                learned_date TEXT,
                FOREIGN KEY (tab_id) REFERENCES tabs (id)
            )
        ''')

        for tuning in ["E A D G B E", "C G C F A D", "D G C F A D"]:
            cursor.execute(
                "INSERT OR IGNORE INTO tunings (name, is_seven_string) VALUES (?, 0)", (tuning,)
            )

        conn.commit()
        conn.close()

        self._migrate_tunings_table()
        self._migrate_notes_column()

    def _migrate_tunings_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(tunings)")
            # BUG FIX 1: was `:[1]` at end — invalid syntax. col[1] extracts column name from pragma row.
            col_names = [col[1] for col in cursor.fetchall()]
            if 'is_seven_string' not in col_names:
                cursor.execute(
                    "ALTER TABLE tunings ADD COLUMN is_seven_string INTEGER DEFAULT 0"
                )
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"Tunings migration warning: {e}")
        finally:
            conn.close()

    def _migrate_notes_column(self):
        """Add notes column to tabs table if it doesn't exist yet (safe migration)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(tabs)")
            # BUG FIX 2: same :[1] syntax error as above
            col_names = [col[1] for col in cursor.fetchall()]
            if 'notes' not in col_names:
                cursor.execute("ALTER TABLE tabs ADD COLUMN notes TEXT DEFAULT ''")
                conn.commit()
                print("Migrated: added 'notes' column to tabs table.")
        except sqlite3.OperationalError as e:
            print(f"Notes migration warning: {e}")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Bands
    # ------------------------------------------------------------------
    def get_all_bands(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM bands ORDER BY name")
        bands = cursor.fetchall()
        conn.close()
        return bands

    def get_band_id(self, band_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bands WHERE name = ?", (band_name,))
        result = cursor.fetchone()
        if result:
            # BUG FIX 3: was `band_id = result` which assigned the whole tuple (id,)
            # instead of the integer id value
            band_id = result[0]
        else:
            cursor.execute("INSERT INTO bands (name) VALUES (?)", (band_name,))
            band_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return band_id

    def clean_up_empty_bands(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.id FROM bands b
                LEFT JOIN tabs t ON b.id = t.band_id
                WHERE t.id IS NULL
            ''')
            empty = cursor.fetchall()
            for (band_id,) in empty:
                cursor.execute("DELETE FROM bands WHERE id = ?", (band_id,))
            conn.commit()
            return len(empty)
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error cleaning up empty bands: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    def get_all_tabs(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre, t.notes
            FROM tabs t
            JOIN bands b ON t.band_id = b.id
            ORDER BY b.name, t.album, t.title
        ''')
        tabs = cursor.fetchall()
        conn.close()
        return tabs

    def get_tabs_for_band(self, band_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating, t.genre, t.notes
            FROM tabs t
            JOIN bands b ON t.band_id = b.id
            WHERE t.band_id = ?
            ORDER BY t.album, t.title
        ''', (band_id,))
        tabs = cursor.fetchall()
        conn.close()
        return tabs

    def add_tab(self, tab_data):
        if self.tab_exists(tab_data["band"], tab_data["album"], tab_data["title"]):
            raise ValueError(
                f"A tab for '{tab_data['title']}' by '{tab_data['band']}' "
                f"from album '{tab_data['album']}' already exists"
            )
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            band_id = self.get_band_id(tab_data["band"])
            is_seven = tab_data.get('is_seven_string', False)
            cursor.execute("SELECT id FROM tunings WHERE name = ?", (tab_data["tuning"],))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO tunings (name, is_seven_string) VALUES (?, ?)",
                    (tab_data["tuning"], 1 if is_seven else 0)
                )
            cursor.execute('''
                INSERT INTO tabs (band_id, album, title, tuning, rating, genre, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                band_id, tab_data["album"], tab_data["title"],
                tab_data["tuning"], tab_data["rating"], tab_data["genre"],
                tab_data.get("notes", "")
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_tab(self, tab_id, tab_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            band_id = self.get_band_id(tab_data["band"])
            is_seven = tab_data.get('is_seven_string', False)
            cursor.execute("SELECT id FROM tunings WHERE name = ?", (tab_data["tuning"],))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO tunings (name, is_seven_string) VALUES (?, ?)",
                    (tab_data["tuning"], 1 if is_seven else 0)
                )
            cursor.execute('''
                UPDATE tabs
                SET band_id = ?, album = ?, title = ?, tuning = ?, rating = ?, genre = ?, notes = ?
                WHERE id = ?
            ''', (
                band_id, tab_data["album"], tab_data["title"],
                tab_data["tuning"], tab_data["rating"], tab_data["genre"],
                tab_data.get("notes", ""),
                tab_id
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_rating(self, tab_id, rating):
        """Lightweight rating-only update — used for inline star clicks and bulk rating."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE tabs SET rating = ? WHERE id = ?", (rating, tab_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_tab(self, tab_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM learned_tabs WHERE tab_id = ?", (tab_id,))
            cursor.execute("DELETE FROM tabs WHERE id = ?", (tab_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def tab_exists(self, band_name, album, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM bands WHERE name = ?", (band_name,))
            result = cursor.fetchone()
            if not result:
                return False
            # BUG FIX 4: was passing `result` (a tuple) as band_id parameter.
            # Must pass result[0] (the integer id).
            cursor.execute(
                "SELECT COUNT(*) FROM tabs WHERE band_id = ? AND album = ? AND title = ?",
                (result[0], album, title)
            )
            # BUG FIX 5: fetchone() returns a tuple like (0,) or (1,) — comparing
            # a tuple to 0 with `> 0` is always True. Must unpack with [0].
            return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"Error checking for duplicate tab: {e}")
            return False
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Tunings
    # ------------------------------------------------------------------
    def get_all_tunings(self, seven_string=False):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM tunings WHERE is_seven_string = ? ORDER BY name",
            (1 if seven_string else 0,)
        )
        # Each row is a tuple like ('E A D G B E',) — extract the string
        tunings = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tunings

    def add_tuning(self, tuning_name, is_seven_string=False):
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM tabs WHERE tuning = ?", (tuning_name,))
            # fetchone() returns a tuple — must unpack
            if cursor.fetchone()[0] > 0:
                return False
            cursor.execute("DELETE FROM tunings WHERE name = ?", (tuning_name,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting tuning: {e}")
            return False
        finally:
            conn.close()

    # ------------------------------------------------------------------
    def get_tab_id(self, band, album, title):
        """Return the tab id for a given band/album/title, or None if not found."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.id FROM tabs t
            JOIN bands b ON t.band_id = b.id
            WHERE b.name = ? AND t.album = ? AND t.title = ?
        ''', (band, album, title))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def is_learned(self, tab_id):
        """Return True if the tab is already in the learned_tabs table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM learned_tabs WHERE tab_id = ?", (tab_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def update_tuning(self, old_name, new_name, is_seven_string):
        """Rename a tuning entry in the tunings table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE tunings SET name = ?, is_seven_string = ? WHERE name = ?",
                (new_name, 1 if is_seven_string else 0, old_name)
            )
            cursor.execute(
                "UPDATE tabs SET tuning = ? WHERE tuning = ?",
                (new_name, old_name)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def mark_as_learned(self, tab_id):
        """Alias for add_to_learned used by the import logic."""
        return self.add_to_learned(tab_id)

    # Learned tabs
    # ------------------------------------------------------------------
    def add_to_learned(self, tab_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM learned_tabs WHERE tab_id = ?", (tab_id,))
            if cursor.fetchone():
                return False
            cursor.execute(
                "INSERT INTO learned_tabs (tab_id, learned_date) VALUES (?, ?)",
                (tab_id, datetime.now().strftime('%Y-%m-%d'))
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def remove_from_learned(self, tab_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM learned_tabs WHERE tab_id = ?", (tab_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_all_learned_tabs(self):
        """Returns: (id, band, album, title, tuning, rating, genre, notes, learned_date)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.id, b.name, t.album, t.title, t.tuning, t.rating,
                   t.genre, t.notes, lt.learned_date
            FROM tabs t
            JOIN bands b ON t.band_id = b.id
            JOIN learned_tabs lt ON t.id = lt.tab_id
            ORDER BY b.name, t.album, t.title
        ''')
        tabs = cursor.fetchall()
        conn.close()
        return tabs

    def update_learned_date(self, tab_id, date_str):
        """Update the learned date for a tab."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE learned_tabs SET learned_date = ? WHERE tab_id = ?",
                (date_str, tab_id)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


