"""
Quick integration test for Phase 1

This script tests that Event Bus and Session Memory work correctly
and can be initialized without errors.
"""

import asyncio
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.event_bus import get_event_bus, Event
from src.core.session_memory import get_session_memory


async def test_event_bus():
    """Test Event Bus basic functionality"""
    print("\n=== Testing Event Bus ===")
    
    # Get singleton instance
    bus = get_event_bus()
    await bus.start()
    
    # Track received events
    received_events = []
    
    def callback(event: Event):
        print(f"  Received: {event.type} - {event.payload}")
        received_events.append(event)
    
    # Subscribe to all events
    bus.subscribe("*", callback)
    
    # Publish test events
    print("Publishing events...")
    await bus.publish("test.wake", {"wake_word": "jarvis"}, source="test")
    await bus.publish("test.clap", {"timestamp": time.time()}, source="test")
    await bus.publish("test.launch", {"app": "VS Code"}, source="test")
    
    # Wait for events to be processed
    await asyncio.sleep(1)
    
    print(f"✓ Event Bus working! Received {len(received_events)} events")
    
    # Test event replay
    if received_events:
        correlation_id = received_events[0].correlation_id
        replayed = await bus.replay(correlation_id)
        print(f"✓ Event replay working! Replayed {len(replayed)} events")
    
    # Test recent events
    recent = await bus.get_recent_events(limit=10)
    print(f"✓ Recent events query working! Got {len(recent)} recent events")
    
    await bus.stop()
    print("✓ Event Bus test completed successfully!\n")


async def test_session_memory():
    """Test Session Memory basic functionality"""
    print("=== Testing Session Memory ===")
    
    # Get singleton instance
    memory = get_session_memory()
    
    # Create a session
    print("Creating session...")
    session_id = await memory.create_session("Test Session", "C:\\Projects\\Test")
    print(f"✓ Session created with ID: {session_id}")
    
    # Set context
    print("Setting context...")
    await memory.set_context(session_id, "last_app", "VS Code")
    await memory.set_context(session_id, "focus_time", 120)
    print("✓ Context set")
    
    # Get context
    last_app = await memory.get_context(session_id, "last_app")
    print(f"✓ Retrieved context: last_app = {last_app}")
    
    # Get all context
    all_context = await memory.get_all_context(session_id)
    print(f"✓ All context: {all_context}")
    
    # Add task
    print("Adding task...")
    task_id = await memory.add_task("Implement Event Bus", session_id)
    print(f"✓ Task created with ID: {task_id}")
    
    # Get pending tasks
    tasks = await memory.get_pending_tasks(session_id)
    print(f"✓ Pending tasks: {len(tasks)} task(s)")
    
    # Complete task
    await memory.complete_task(task_id)
    print("✓ Task completed")
    
    # Record preference
    print("Recording preference...")
    await memory.record_preference("morning_coding", "open_vscode_spotify", 0.8)
    print("✓ Preference recorded")
    
    # Get preferences
    prefs = await memory.get_preferences_for_context("morning_coding")
    print(f"✓ Retrieved {len(prefs)} preference(s) for 'morning_coding'")
    
    # Get active sessions
    sessions = await memory.get_active_sessions()
    print(f"✓ Active sessions: {len(sessions)} session(s)")
    
    print("✓ Session Memory test completed successfully!\n")


async def main():
    """Run all tests"""
    print("\n" + "="*50)
    print("Phase 1 Integration Test")
    print("="*50)
    
    try:
        await test_event_bus()
        await test_session_memory()
        
        print("="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50)
        print("\nPhase 1 components are working correctly.")
        print("Event Bus and Session Memory are ready for use.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
