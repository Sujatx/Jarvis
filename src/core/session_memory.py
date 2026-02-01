"""
Session Memory - Persistent storage for workspace context, tasks, and learned preferences

This module provides a SQLite-based memory system for Jarvis to track:
- Active work sessions and project context
- Pending tasks and reminders
- Learned user preferences
- Session-specific contextual data

All operations are async to avoid blocking the main event loop.
"""

import asyncio
import sqlite3
import json
import time
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import aiosqlite


@dataclass
class Session:
    """Represents a work session"""
    id: Optional[int]
    name: str
    started_at: float
    last_active: float
    project_path: Optional[str]
    is_active: bool
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "started_at": self.started_at,
            "last_active": self.last_active,
            "project_path": self.project_path,
            "is_active": self.is_active
        }


@dataclass
class Task:
    """Represents a pending task or reminder"""
    id: Optional[int]
    session_id: Optional[int]
    description: str
    status: str  # pending, completed, cancelled
    created_at: float
    completed_at: Optional[float]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


@dataclass
class Preference:
    """Represents a learned user preference"""
    id: Optional[int]
    context: str
    action: str
    confidence: float
    learned_at: float
    last_used: Optional[float]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "context": self.context,
            "action": self.action,
            "confidence": self.confidence,
            "learned_at": self.learned_at,
            "last_used": self.last_used
        }


class SessionMemory:
    """
    Session Memory database for Jarvis
    
    Provides async  operations for:
    - Session management (create, read, update, archive)
    - Context tracking (key-value storage per session)
    - Task management (create, complete, list pending)
    - Preference learning (record, retrieve, update confidence)
    """
    
    def __init__(self, db_path: str = "jarvis_sessions.db"):
        """
        Initialize Session Memory
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema (synchronous, called once at startup)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                started_at REAL NOT NULL,
                last_active REAL NOT NULL,
                project_path TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Session context (flexible key-value storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Pending tasks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL NOT NULL,
                completed_at REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
        """)
        
        # Learned preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                learned_at REAL NOT NULL,
                last_used REAL
            )
        """)
        
        # Indices for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_active 
            ON sessions(is_active)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_session 
            ON session_context(session_id, key)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status 
            ON pending_tasks(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_preferences_context 
            ON learned_preferences(context)
        """)
        
        conn.commit()
        conn.close()
    
    # Session Management
    
    async def create_session(self, name: str, project_path: Optional[str] = None) -> int:
        """
        Create a new work session
        
        Args:
            name: Name of the session (e.g., "Work on Jarvis Evolution")
            project_path: Optional path to project directory
            
        Returns:
            Session ID
        """
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO sessions (name, started_at, last_active, project_path, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (name, now, now, project_path))
            
            await db.commit()
            return cursor.lastrowid
    
    async def get_session(self, session_id: int) -> Optional[Session]:
        """Get session by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM sessions WHERE id = ?
            """, (session_id,))
            
            row = await cursor.fetchone()
            
            if row:
                return Session(
                    id=row["id"],
                    name=row["name"],
                    started_at=row["started_at"],
                    last_active=row["last_active"],
                    project_path=row["project_path"],
                    is_active=bool(row["is_active"])
                )
            return None
    
    async def get_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM sessions 
                WHERE is_active = 1 
                ORDER BY last_active DESC
            """)
            
            rows = await cursor.fetchall()
            
            return [
                Session(
                    id=row["id"],
                    name=row["name"],
                    started_at=row["started_at"],
                    last_active=row["last_active"],
                    project_path=row["project_path"],
                    is_active=bool(row["is_active"])
                )
                for row in rows
            ]
    
    async def update_session_activity(self, session_id: int):
        """Update last_active timestamp for a session"""
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET last_active = ? 
                WHERE id = ?
            """, (now, session_id))
            
            await db.commit()
    
    async def archive_session(self, session_id: int):
        """Archive a session (set is_active to 0)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET is_active = 0 
                WHERE id = ?
            """, (session_id,))
            
            await db.commit()
    
    # Context Management
    
    async def set_context(self, session_id: int, key: str, value: Any):
        """
        Set a context value for a session
        
        Args:
            session_id: Session ID
            key: Context key (e.g., "last_opened_app")
            value: Value (will be JSON serialized)
        """
        now = time.time()
        value_json = json.dumps(value)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if key exists
            cursor = await db.execute("""
                SELECT id FROM session_context 
                WHERE session_id = ? AND key = ?
            """, (session_id, key))
            
            row = await cursor.fetchone()
            
            if row:
                # Update existing
                await db.execute("""
                    UPDATE session_context 
                    SET value = ?, updated_at = ? 
                    WHERE session_id = ? AND key = ?
                """, (value_json, now, session_id, key))
            else:
                # Insert new
                await db.execute("""
                    INSERT INTO session_context (session_id, key, value, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, key, value_json, now))
            
            await db.commit()
            
            # Update session activity
            await self.update_session_activity(session_id)
    
    async def get_context(self, session_id: int, key: str) -> Optional[Any]:
        """Get a context value for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT value FROM session_context 
                WHERE session_id = ? AND key = ?
            """, (session_id, key))
            
            row = await cursor.fetchone()
            
            if row:
                return json.loads(row[0])
            return None
    
    async def get_all_context(self, session_id: int) -> Dict[str, Any]:
        """Get all context for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT key, value FROM session_context 
                WHERE session_id = ?
            """, (session_id,))
            
            rows = await cursor.fetchall()
            
            return {
                row["key"]: json.loads(row["value"])
                for row in rows
            }
    
    # Task Management
    
    async def add_task(self, description: str, session_id: Optional[int] = None) -> int:
        """
        Add a pending task
        
        Args:
            description: Task description
            session_id: Optional session to associate with
            
        Returns:
            Task ID
        """
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO pending_tasks (session_id, description, status, created_at)
                VALUES (?, ?, 'pending', ?)
            """, (session_id, description, now))
            
            await db.commit()
            return cursor.lastrowid
    
    async def complete_task(self, task_id: int):
        """Mark a task as completed"""
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE pending_tasks 
                SET status = 'completed', completed_at = ? 
                WHERE id = ?
            """, (now, task_id))
            
            await db.commit()
    
    async def cancel_task(self, task_id: int):
        """Cancel a task"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE pending_tasks 
                SET status = 'cancelled' 
                WHERE id = ?
            """, (task_id,))
            
            await db.commit()
    
    async def get_pending_tasks(self, session_id: Optional[int] = None) -> List[Task]:
        """
        Get all pending tasks
        
        Args:
            session_id: Optional filter by session
            
        Returns:
            List of pending tasks
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if session_id is not None:
                cursor = await db.execute("""
                    SELECT * FROM pending_tasks 
                    WHERE status = 'pending' AND session_id = ?
                    ORDER BY created_at ASC
                """, (session_id,))
            else:
                cursor = await db.execute("""
                    SELECT * FROM pending_tasks 
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                """)
            
            rows = await cursor.fetchall()
            
            return [
                Task(
                    id=row["id"],
                    session_id=row["session_id"],
                    description=row["description"],
                    status=row["status"],
                    created_at=row["created_at"],
                    completed_at=row["completed_at"]
                )
                for row in rows
            ]
    
    # Preference Learning
    
    async def record_preference(self, context: str, action: str, confidence: float = 0.5):
        """
        Record a learned preference
        
        Args:
            context: Context identifier (e.g., "morning_coding")
            action: Action taken (e.g., "open_vscode_with_spotify")
            confidence: Confidence score (0.0 to 1.0)
        """
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if preference exists
            cursor = await db.execute("""
                SELECT id, confidence FROM learned_preferences 
                WHERE context = ? AND action = ?
            """, (context, action))
            
            row = await cursor.fetchone()
            
            if row:
                # Update existing - increase confidence
                old_confidence = row[1]
                new_confidence = min(1.0, old_confidence + 0.1)
                
                await db.execute("""
                    UPDATE learned_preferences 
                    SET confidence = ?, last_used = ? 
                    WHERE id = ?
                """, (new_confidence, now, row[0]))
            else:
                # Insert new
                await db.execute("""
                    INSERT INTO learned_preferences (context, action, confidence, learned_at, last_used)
                    VALUES (?, ?, ?, ?, ?)
                """, (context, action, confidence, now, now))
            
            await db.commit()
    
    async def get_preferences_for_context(self, context: str, min_confidence: float = 0.5) -> List[Preference]:
        """
        Get learned preferences for a context
        
        Args:
            context: Context identifier
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of preferences sorted by confidence (descending)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM learned_preferences 
                WHERE context = ? AND confidence >= ?
                ORDER BY confidence DESC
            """, (context, min_confidence))
            
            rows = await cursor.fetchall()
            
            return [
                Preference(
                    id=row["id"],
                    context=row["context"],
                    action=row["action"],
                    confidence=row["confidence"],
                    learned_at=row["learned_at"],
                    last_used=row["last_used"]
                )
                for row in rows
            ]
    
    async def get_all_preferences(self) -> List[Preference]:
        """Get all learned preferences"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM learned_preferences 
                ORDER BY confidence DESC, last_used DESC
            """)
            
            rows = await cursor.fetchall()
            
            return [
                Preference(
                    id=row["id"],
                    context=row["context"],
                    action=row["action"],
                    confidence=row["confidence"],
                    learned_at=row["learned_at"],
                    last_used=row["last_used"]
                )
                for row in rows
            ]


# Singleton instance for global access
_session_memory_instance: Optional[SessionMemory] = None


def get_session_memory(db_path: str = None) -> SessionMemory:
    """
    Get or create the global SessionMemory instance
    
    Args:
        db_path: Optional path to database (only used on first call)
        
    Returns:
        Global SessionMemory instance
    """
    global _session_memory_instance
    
    if _session_memory_instance is None:
        # Determine db_path
        if db_path is None:
            # Use default path relative to script location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "jarvis_sessions.db")
        
        _session_memory_instance = SessionMemory(db_path=db_path)
    
    return _session_memory_instance
