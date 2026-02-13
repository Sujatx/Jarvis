"""
Database Manager - Handles SQLite connection and initialization for persistent memory.
"""

import sqlite3
import os
import threading
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path="jarvis_memory.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance.db_path = db_path
                    cls._instance.connection = None
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the database connection and schema."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._create_schema()
            logger.info(f"Connected to memory database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _create_schema(self):
        """Load and execute the schema.sql file."""
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if not os.path.exists(schema_path):
            logger.warning("schema.sql not found, skipping table creation.")
            return

        try:
            with open(schema_path, "r") as f:
                schema = f.read()
                self.connection.executescript(schema)
                self.connection.commit()
        except Exception as e:
            logger.error(f"Error executing schema: {e}")

    def get_connection(self):
        """Return the active database connection."""
        return self.connection

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

def get_db():
    return DatabaseManager()
