"""
Unit tests for the Event Bus module
"""

import asyncio
import pytest
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import EventBus, Event, get_event_bus


# Pytest fixtures

@pytest.fixture
async def event_bus():
    """Create a test event bus instance"""
    db_path = "test_events.db"
    
    # Remove old test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    bus = EventBus(db_path=db_path, max_queue_size=100)
    await bus.start()
    
    yield bus
    
    await bus.stop()
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


# Tests

@pytest.mark.asyncio
async def test_event_creation():
    """Test Event dataclass creation and serialization"""
    event = Event(
        type="test.event",
        payload={"key": "value"},
        timestamp=time.time(),
        source="test",
        correlation_id="test-123"
    )
    
    assert event.type == "test.event"
    assert event.payload["key"] == "value"
    assert event.source == "test"
    
    # Test serialization
    event_dict = event.to_dict()
    assert event_dict["type"] == "test.event"
    
    # Test JSON conversion
    event_json = event.to_json()
    assert "test.event" in event_json


@pytest.mark.asyncio
async def test_publish_and_subscribe(event_bus):
    """Test basic publish/subscribe functionality"""
    received_events = []
    
    def callback(event: Event):
        received_events.append(event)
    
    # Subscribe to events
    event_bus.subscribe("test.*", callback)
    
    # Publish event
    await event_bus.publish("test.event", {"data": "hello"}, source="test")
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    # Verify event was received
    assert len(received_events) == 1
    assert received_events[0].type == "test.event"
    assert received_events[0].payload["data"] == "hello"


@pytest.mark.asyncio
async def test_wildcard_subscription(event_bus):
    """Test wildcard pattern matching in subscriptions"""
    app_events = []
    all_events = []
    
    def app_callback(event: Event):
        app_events.append(event)
    
    def all_callback(event: Event):
        all_events.append(event)
    
    # Subscribe with different patterns
    event_bus.subscribe("app.*", app_callback)
    event_bus.subscribe("*", all_callback)
    
    # Publish various events
    await event_bus.publish("app.launched", {"name": "VS Code"}, source="launcher")
    await event_bus.publish("wake.detected", {}, source="porcupine")
    await event_bus.publish("app.failed", {"error": "not found"}, source="launcher")
    
    # Wait for processing
    await asyncio.sleep(0.5)
    
    # Verify app.* received only app events
    assert len(app_events) == 2
    assert all(e.type.startswith("app.") for e in app_events)
    
    # Verify * received all events
    assert len(all_events) == 3


@pytest.mark.asyncio
async def test_event_persistence(event_bus):
    """Test that events are persisted to database"""
    correlation_id = "test-correlation-123"
    
    # Publish events with same correlation ID
    await event_bus.publish("step.1", {"action": "start"}, source="test", correlation_id=correlation_id)
    await event_bus.publish("step.2", {"action": "middle"}, source="test", correlation_id=correlation_id)
    await event_bus.publish("step.3", {"action": "end"}, source="test", correlation_id=correlation_id)
    
    # Wait for persistence
    await asyncio.sleep(0.5)
    
    # Replay events
    replayed = await event_bus.replay(correlation_id)
    
    assert len(replayed) == 3
    assert replayed[0].type == "step.1"
    assert replayed[1].type == "step.2"
    assert replayed[2].type == "step.3"


@pytest.mark.asyncio
async def test_get_recent_events(event_bus):
    """Test retrieving recent events"""
    # Publish several events
    for i in range(5):
        await event_bus.publish(f"test.event.{i}", {"index": i}, source="test")
    
    # Wait for persistence
    await asyncio.sleep(0.5)
    
    # Get recent events
    recent = await event_bus.get_recent_events(limit=10)
    
    assert len(recent) >= 5
    # Should be in reverse chronological order
    assert recent[0].type == "test.event.4"


@pytest.mark.asyncio
async def test_get_recent_events_with_filter(event_bus):
    """Test filtering recent events by type"""
    # Publish mixed events
    await event_bus.publish("app.launched", {}, source="test")
    await event_bus.publish("wake.detected", {}, source="test")
    await event_bus.publish("app.failed", {}, source="test")
    
    # Wait for persistence
    await asyncio.sleep(0.5)
    
    # Get only app events
    app_events = await event_bus.get_recent_events(limit=10, event_type="app.*")
    
    assert len(app_events) == 2
    assert all(e.type.startswith("app.") for e in app_events)


@pytest.mark.asyncio
async def test_async_callback(event_bus):
    """Test that async callbacks work correctly"""
    received_events = []
    
    async def async_callback(event: Event):
        await asyncio.sleep(0.1)  # Simulate async work
        received_events.append(event)
    
    event_bus.subscribe("async.*", async_callback)
    
    await event_bus.publish("async.test", {"data": "hello"}, source="test")
    
    # Wait for async processing
    await asyncio.sleep(0.3)
    
    assert len(received_events) == 1
    assert received_events[0].type == "async.test"


@pytest.mark.asyncio
async def test_unsubscribe(event_bus):
    """Test unsubscribing from events"""
    received_events = []
    
    def callback(event: Event):
        received_events.append(event)
    
    # Subscribe
    event_bus.subscribe("test.*", callback)
    
    # Publish event
    await event_bus.publish("test.before", {}, source="test")
    await asyncio.sleep(0.2)
    
    # Unsubscribe
    event_bus.unsubscribe("test.*", callback)
    
    # Publish another event
    await event_bus.publish("test.after", {}, source="test")
    await asyncio.sleep(0.2)
    
    # Should only have received the first event
    assert len(received_events) == 1
    assert received_events[0].type == "test.before"


@pytest.mark.asyncio
async def test_correlation_tracking():
    """Test that correlation IDs are tracked correctly"""
    db_path = "test_correlation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    bus = EventBus(db_path=db_path)
    await bus.start()
    
    correlation_id = "workflow-123"
    
    # Publish related events
    await bus.publish("workflow.start", {}, source="test", correlation_id=correlation_id)
    await bus.publish("workflow.step1", {}, source="test", correlation_id=correlation_id)
    await bus.publish("workflow.step2", {}, source="test", correlation_id=correlation_id)
    await bus.publish("workflow.complete", {}, source="test", correlation_id=correlation_id)
    
    # Publish unrelated event
    await bus.publish("other.event", {}, source="test")
    
    await asyncio.sleep(0.5)
    
    # Replay correlated events
    related = await bus.replay(correlation_id)
    
    assert len(related) == 4
    assert all(e.correlation_id == correlation_id for e in related)
    
    await bus.stop()
    if os.path.exists(db_path):
        os.remove(db_path)


def test_sync_publish():
    """Test synchronous publish from non-async code"""
    db_path = "test_sync.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    bus = EventBus(db_path=db_path)
    
    # Start bus in background
    async def run_bus():
        await bus.start()
        await asyncio.sleep(2)  # Keep running
        await bus.stop()
    
    # Run in separate thread
    import threading
    
    def bus_thread():
        asyncio.run(run_bus())
    
    thread = threading.Thread(target=bus_thread, daemon=True)
    thread.start()
    
    # Give bus time to start
    time.sleep(0.5)
    
    # Publish from sync code
    bus.publish_sync("sync.test", {"data": "from sync"}, source="test")
    
    # Wait for processing
    time.sleep(0.5)
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
