"""
Jarvis Subconscious - Mark-X Category-Based Memory.
Stores identity, preferences, relationships, emotional state, and session summaries in SQLite.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List
from src.core.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = "jarvis_subconscious.db"

class Subconscious:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Mark-X Categories
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories 
                         (name TEXT PRIMARY KEY, data TEXT)''')
        
        # Episodic Memory (Atomic events)
        cursor.execute('''CREATE TABLE IF NOT EXISTS episodes 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          content TEXT, importance INTEGER, timestamp TIMESTAMP)''')
        
        # Session Summaries (Long-term conversational context)
        cursor.execute('''CREATE TABLE IF NOT EXISTS session_summaries 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          summary TEXT, 
                          timestamp TIMESTAMP)''')
        
        # Seed default categories if empty
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            defaults = [
                ('identity', json.dumps({'name': 'Jarvis', 'version': 'Elite-Session'})),
                ('preferences', json.dumps({})),
                ('relationships', json.dumps({'user': 'Sir'})),
                ('emotional_state', json.dumps({'current': 'Stable'}))
            ]
            cursor.executemany("INSERT INTO categories VALUES (?, ?)", defaults)
            
        conn.commit()
        conn.close()

    def get_context_summary(self) -> str:
        """Condensed memory for the LLM prompt, including recent summaries."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get Categories
        cursor.execute("SELECT name, data FROM categories")
        rows = cursor.fetchall()
        summary_data = {}
        for name, data in rows:
            summary_data[name] = json.loads(data)
            
        # Get Recent Session Summaries (Last 5)
        cursor.execute("SELECT summary FROM session_summaries ORDER BY timestamp DESC LIMIT 5")
        past_summaries = [row[0] for row in cursor.fetchall()]
        summary_data['past_sessions'] = past_summaries
        
        # Get Recent Episodes
        cursor.execute("SELECT content FROM episodes ORDER BY timestamp DESC LIMIT 3")
        memories = [m[0] for m in cursor.fetchall()]
        summary_data['recent_episodes'] = memories
        
        conn.close()
        return json.dumps(summary_data)

    def save_session_summary(self, summary: str):
        """Persist a summarized session."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO session_summaries (summary, timestamp) VALUES (?, ?)", 
                       (summary, datetime.now()))
        conn.commit()
        conn.close()
        logger.info("Subconscious: Session summary persisted.")

    def get_recent_summaries(self, limit: int = 3) -> str:
        """Fetch the last few session summaries as a single string."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT summary FROM session_summaries ORDER BY timestamp DESC LIMIT ?", (limit,))
        summaries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return " | ".join(summaries) if summaries else "No previous sessions."

    def update_category(self, category: str, updates: dict):
        """Merge new info into a specific category."""
        if not updates or not isinstance(updates, dict): return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT data FROM categories WHERE name = ?", (category,))
            row = cursor.fetchone()
            current_data = json.loads(row[0]) if row else {}
            
            # Deep Merge
            current_data.update(updates)
            
            cursor.execute("INSERT OR REPLACE INTO categories VALUES (?, ?)", 
                           (category, json.dumps(current_data)))
            conn.commit()
        except Exception as e:
            logger.error(f"Memory Update Error ({category}): {e}")
        finally:
            conn.close()

    def add_episode(self, content: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO episodes (content, importance, timestamp) VALUES (?, ?, ?)", 
                       (content, 1, datetime.now()))
        conn.commit()
        conn.close()

MEMORY = Subconscious()
