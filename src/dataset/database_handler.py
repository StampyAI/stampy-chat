import os
import sqlite3
from typing import List, Dict, Any

import logging
logger = logging.getLogger(__name__)


class DatabaseHandler:
    def __init__(
        self, 
        db_name: str = "data\\alignment_database.db",
    ):
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.realpath(__file__))

        # Combine the script directory with the relative database path
        self.db_name = os.path.join(script_dir, db_name)
        
        self.create_tables()

    def create_tables(self, reset: bool = False):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            try:
                if reset:
                    # Drop the tables if reset is True
                    cursor.execute("DROP TABLE IF EXISTS entry_database")
                    cursor.execute("DROP TABLE IF EXISTS chunk_database")
                
                # Create entry table
                query = """
                    CREATE TABLE IF NOT EXISTS entry_database (
                        id TEXT PRIMARY KEY,
                        source TEXT,
                        title TEXT,
                        text TEXT,
                        url TEXT,
                        date_published TEXT,
                        authors TEXT
                    )
                """
                cursor.execute(query)

                # Create chunk table
                query = """
                    CREATE TABLE IF NOT EXISTS chunk_database (
                        id TEXT PRIMARY KEY,
                        text TEXT,
                        entry_id TEXT,
                        FOREIGN KEY (entry_id) REFERENCES entry_database(id)
                    )
                """
                cursor.execute(query)

            except sqlite3.Error as e:
                logger.error(f"The error '{e}' occurred.")

    def upsert_entry(self, entry: Dict[str, Any]) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            try:
                # Fetch existing data
                cursor.execute("SELECT * FROM entry_database WHERE id=?", (entry['id'],))
                existing_entry = cursor.fetchone()

                new_entry = (
                    entry['id'],
                    entry['source'],
                    entry['title'],
                    entry['text'],
                    entry['url'],
                    entry['date_published'],
                    ', '.join(entry['authors'])
                )

                if existing_entry != new_entry:
                    query = """
                        INSERT OR REPLACE INTO entry_database
                        (id, source, title, text, url, date_published, authors)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(query, new_entry)
                    return True
                else:
                    return False

            except sqlite3.Error as e:
                logger.error(f"The error '{e}' occurred.")
                return False

            finally:
                conn.commit()

    def upsert_chunks(self, entry_id: str, chunks: List[str]) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            try:
                # Delete existing chunks
                cursor.execute("DELETE FROM chunk_database WHERE entry_id=?", (entry_id,))

                # Insert new chunks
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{entry_id}_{str(i).zfill(6)}"
                    cursor.execute("INSERT INTO chunk_database (id, text, entry_id) VALUES (?, ?, ?)", (chunk_id, chunk, entry_id))
                return True
                
            except sqlite3.Error as e:
                logger.error(f"The error '{e}' occurred.")
                return False

            finally:
                conn.commit()