# dataset/sql_db_handler.py

from typing import List, Dict, Union
import sqlite3

from .settings import SQL_DB_PATH

import logging
logger = logging.getLogger(__name__)


class SQLDB:
    def __init__(self):
        self.db_name = SQL_DB_PATH
        
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

    def upsert_entry(self, entry: Dict[str, Union[str, list]]) -> bool:
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
    
    def upsert_chunks(self, chunks_ids_batch: List[str], chunks_batch: List[str]) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            try:
                for chunk_id, chunk in zip(chunks_ids_batch, chunks_batch):
                    cursor.execute("""
                        INSERT OR REPLACE INTO chunk_database
                        (id, text)
                        VALUES (?, ?)
                    """, (chunk_id, chunk))
            except sqlite3.Error as e:
                logger.error(f"The error '{e}' occurred.")
            finally:
                conn.commit()
