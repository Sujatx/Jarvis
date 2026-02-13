"""
Repositories - CRUD operations for persistent memory.
"""

import uuid
from datetime import datetime
from src.core.memory.database import get_db

class TaskRepository:
    def __init__(self):
        self.db = get_db().get_connection()

    def add_task(self, content, due_date=None, priority=1):
        task_id = str(uuid.uuid4())
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO tasks (id, content, due_date, priority) VALUES (?, ?, ?, ?)",
            (task_id, content, due_date, priority)
        )
        self.db.commit()
        return task_id

    def list_tasks(self, status="pending"):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC", (status,))
        return [dict(row) for row in cursor.fetchall()]

    def complete_task(self, task_id):
        cursor = self.db.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        self.db.commit()
        return cursor.rowcount > 0

class CalendarRepository:
    def __init__(self):
        self.db = get_db().get_connection()

    def add_event(self, title, start_time, end_time=None, location=None):
        event_id = str(uuid.uuid4())
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO calendar_events (id, title, start_time, end_time, location) VALUES (?, ?, ?, ?, ?)",
            (event_id, title, start_time, end_time, location)
        )
        self.db.commit()
        return event_id

    def list_events(self, date_str=None):
        cursor = self.db.cursor()
        if date_str:
            # Simple day filtering (assuming ISO format YYYY-MM-DD)
            cursor.execute("SELECT * FROM calendar_events WHERE date(start_time) = ? ORDER BY start_time ASC", (date_str,))
        else:
            cursor.execute("SELECT * FROM calendar_events ORDER BY start_time ASC")
        return [dict(row) for row in cursor.fetchall()]
