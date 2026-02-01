"""
Event Bus - Central message queue for decoupled component communication

This module provides an event-driven architecture foundation for Jarvis,
enabling components to communicate through events rather than direct method calls.

Features:
- AsyncIO-based non-blocking event queue
- Topic-based publish/subscribe pattern
- Event persistence to SQLite for debugging and replay
- Correlation IDs for tracking multi-step operations
- Thread-safe bridge between sync and async code
"""

import asyncio
import json
import time
import uuid
import re
import sqlite3
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
import os


@dataclass
class Event:
    """Standardized event structure"""
    type: str                    # e.g., "app.launched", "wake.detected"
    payload: Dict[str, Any]      # Event-specific data
    timestamp: float             # Unix timestamp
    source: str                  # Component that published the event
    correlation_id: str          # UUID for tracking related events
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """Create Event from dictionary"""
        return cls(**data)


class EventBus:
    """
    Central event bus for Jarvis with async message queue and persistence.
    
    Thread-safe: Can be called from sync code using the bridge methods.
    """
    
    def __init__(self, db_path: str = "jarvis_events.db", max_queue_size: int = 1000):
        """
        Initialize the Event Bus
        
        Args:
            db_path: Path to SQLite database for event persistence
            max_queue_size: Maximum number of events in the queue
        """
        self.db_path = db_path
        self.max_queue_size = max_queue_size
        
        # AsyncIO components
        self._queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for event persistence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp REAL NOT NULL,
                source TEXT NOT NULL,
                correlation_id TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Index for faster correlation_id lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_correlation_id 
            ON event_log(correlation_id)
        """)
        
        # Index for faster type-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_type 
            ON event_log(type)
        """)
        
        conn.commit()
        conn.close()
    
    async def start(self):
        """Start the event bus worker"""
        if self._running:
            return
        
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=self.max_queue_size)
        self._worker_task = asyncio.create_task(self._process_events())
    
    async def stop(self):
        """Stop the event bus worker"""
        if not self._running:
            return
        
        self._running = False
        
        # Wait for queue to drain
        if self._queue:
            await self._queue.join()
        
        # Cancel worker task
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
    
    async def _process_events(self):
        """Worker coroutine that processes events from the queue"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                
                # Persist to database
                await self._persist_event(event)
                
                # Notify subscribers
                await self._notify_subscribers(event)
                
                # Mark task as done
                self._queue.task_done()
                
            except asyncio.TimeoutError:
                # No events, continue waiting
                continue
            except Exception as e:
                print(f"[EventBus] Error processing event: {e}")
    
    async def _persist_event(self, event: Event):
        """Persist event to database"""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_event_to_db, event)
        except Exception as e:
            print(f"[EventBus] Error persisting event: {e}")
    
    def _write_event_to_db(self, event: Event):
        """Synchronous database write (called in executor)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO event_log (type, payload, timestamp, source, correlation_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.type,
            json.dumps(event.payload),
            event.timestamp,
            event.source,
            event.correlation_id
        ))
        
        conn.commit()
        conn.close()
    
    async def _notify_subscribers(self, event: Event):
        """Notify all subscribers matching the event type"""
        matching_subscribers = []
        
        with self._lock:
            for pattern, subscribers in self._subscribers.items():
                if self._matches_pattern(event.type, pattern):
                    matching_subscribers.extend(subscribers)
        
        # Call subscribers
        for subscriber in matching_subscribers:
            try:
                # Support both sync and async callbacks
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    await asyncio.get_running_loop().run_in_executor(None, subscriber, event)
            except Exception as e:
                print(f"[EventBus] Error in subscriber: {e}")
    
    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """
        Check if event type matches subscription pattern
        
        Supports wildcards:
        - "app.*" matches "app.launched", "app.failed", etc.
        - "*" matches everything
        """
        if pattern == "*":
            return True
        
        # Convert glob pattern to regex
        regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
        return re.match(f"^{regex_pattern}$", event_type) is not None
    
    async def publish(self, event_type: str, payload: Dict[str, Any], 
                     source: str = "unknown", correlation_id: Optional[str] = None):
        """
        Publish an event to the bus
        
        Args:
            event_type: Type of event (e.g., "app.launched")
            payload: Event-specific data
            source: Component publishing the event
            correlation_id: Optional correlation ID for tracking related events
        """
        if not self._running or not self._queue:
            raise RuntimeError("EventBus not started. Call start() first.")
        
        event = Event(
            type=event_type,
            payload=payload,
            timestamp=time.time(),
            source=source,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        
        try:
            await self._queue.put(event)
        except asyncio.QueueFull:
            print(f"[EventBus] Queue full, dropping event: {event_type}")
    
    def subscribe(self, pattern: str, callback: Callable):
        """
        Subscribe to events matching a pattern
        
        Args:
            pattern: Event type pattern (supports wildcards like "app.*")
            callback: Function to call when matching event occurs
        """
        with self._lock:
            self._subscribers[pattern].append(callback)
    
    def unsubscribe(self, pattern: str, callback: Callable):
        """Unsubscribe from events"""
        with self._lock:
            if pattern in self._subscribers:
                self._subscribers[pattern].remove(callback)
    
    async def replay(self, correlation_id: str) -> List[Event]:
        """
        Replay all events with a given correlation ID
        
        Args:
            correlation_id: Correlation ID to filter events
            
        Returns:
            List of events in chronological order
        """
        loop = asyncio.get_running_loop()
        events = await loop.run_in_executor(None, self._get_events_by_correlation, correlation_id)
        return events
    
    def _get_events_by_correlation(self, correlation_id: str) -> List[Event]:
        """Synchronous database query for event replay"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT type, payload, timestamp, source, correlation_id
            FROM event_log
            WHERE correlation_id = ?
            ORDER BY timestamp ASC
        """, (correlation_id,))
        
        events = []
        for row in cursor.fetchall():
            event = Event(
                type=row[0],
                payload=json.loads(row[1]),
                timestamp=row[2],
                source=row[3],
                correlation_id=row[4]
            )
            events.append(event)
        
        conn.close()
        return events
    
    async def get_recent_events(self, limit: int = 100, event_type: Optional[str] = None) -> List[Event]:
        """
        Get recent events from the log
        
        Args:
            limit: Maximum number of events to return
            event_type: Optional filter by event type (supports wildcards)
            
        Returns:
            List of recent events in reverse chronological order
        """
        loop = asyncio.get_running_loop()
        events = await loop.run_in_executor(None, self._get_recent_events_sync, limit, event_type)
        return events
    
    def _get_recent_events_sync(self, limit: int, event_type: Optional[str]) -> List[Event]:
        """Synchronous database query for recent events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if event_type:
            # Convert wildcard pattern to SQL LIKE pattern
            sql_pattern = event_type.replace("*", "%")
            cursor.execute("""
                SELECT type, payload, timestamp, source, correlation_id
                FROM event_log
                WHERE type LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (sql_pattern, limit))
        else:
            cursor.execute("""
                SELECT type, payload, timestamp, source, correlation_id
                FROM event_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        events = []
        for row in cursor.fetchall():
            event = Event(
                type=row[0],
                payload=json.loads(row[1]),
                timestamp=row[2],
                source=row[3],
                correlation_id=row[4]
            )
            events.append(event)
        
        conn.close()
        return events
    
    # Thread-safe bridge methods for calling from synchronous code
    
    def publish_sync(self, event_type: str, payload: Dict[str, Any], 
                    source: str = "unknown", correlation_id: Optional[str] = None):
        """
        Thread-safe synchronous publish (for calling from sync code)
        
        This creates a task in the event loop without waiting for it to complete.
        """
        if not self._loop or not self._running:
            print(f"[EventBus] Cannot publish, bus not running: {event_type}")
            return
        
        asyncio.run_coroutine_threadsafe(
            self.publish(event_type, payload, source, correlation_id),
            self._loop
        )


# Singleton instance for global access
_event_bus_instance: Optional[EventBus] = None
_event_bus_lock = threading.Lock()


def get_event_bus(db_path: str = None) -> EventBus:
    """
    Get or create the global EventBus instance
    
    Args:
        db_path: Optional path to database (only used on first call)
        
    Returns:
        Global EventBus instance
    """
    global _event_bus_instance
    
    with _event_bus_lock:
        if _event_bus_instance is None:
            # Determine db_path
            if db_path is None:
                # Use default path relative to script location
                script_dir = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.join(script_dir, "jarvis_events.db")
            
            _event_bus_instance = EventBus(db_path=db_path)
        
        return _event_bus_instance


# Convenience functions for common operations

async def publish_event(event_type: str, payload: Dict[str, Any], 
                       source: str = "unknown", correlation_id: Optional[str] = None):
    """Convenience function to publish an event"""
    bus = get_event_bus()
    await bus.publish(event_type, payload, source, correlation_id)


def publish_event_sync(event_type: str, payload: Dict[str, Any], 
                      source: str = "unknown", correlation_id: Optional[str] = None):
    """Convenience function to publish an event from sync code"""
    bus = get_event_bus()
    bus.publish_sync(event_type, payload, source, correlation_id)


def subscribe_to_events(pattern: str, callback: Callable):
    """Convenience function to subscribe to events"""
    bus = get_event_bus()
    bus.subscribe(pattern, callback)
