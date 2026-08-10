"""Database connection module."""
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager."""
    
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            logger.info("Database initialized")
    
    def execute(self, query: str, params: tuple = ()):
        """Execute a query."""
        with self.get_connection() as conn:
            return conn.execute(query, params)
    
    def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows from a query."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def fetch_one(self, query: str, params: tuple = ()):
        """Fetch one row from a query."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()
