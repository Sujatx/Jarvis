"""
Test Local Fallback Execution Layer
Verifies LocalRouter and offline capabilities
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cognitive.local_router import LocalRouter
from src.cognitive.agent_router import AgentRouter
from src.tools.registry import register
from src.tools.base_tool import BaseTool


# Mock tools for testing
class MockOpenApp(BaseTool):
    name = "open_app"
    description = "Open an application"
    schema = {
        "name": "open_app",
        "parameters": {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"]
        }
    }
    
    async def execute(self, target: str = "", **kwargs):
        return {"status": "success", "message": f"Opened {target}"}


class MockOpenWebsite(BaseTool):
    name = "open_website"
    description = "Open a website"
    schema = {
        "name": "open_website",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "browser": {"type": "string"}
            },
            "required": ["url"]
        }
    }
    
    async def execute(self, url: str = "", browser: str = None, **kwargs):
        return {"status": "success", "message": f"Opened {url}"}


# Register mock tools
register(MockOpenApp)
register(MockOpenWebsite)


async def test_local_router():
    """Test LocalRouter pattern matching."""
    print("\n=== Test 1: LocalRouter Pattern Matching ===")
    
    router = LocalRouter()
    
    # Test greeting
    result = router.route("hello")
    assert result is not None, "Should match greeting"
    assert result["type"] == "chat", "Greeting should be chat"
    print("✓ Greeting matches")
    
    # Test time query
    result = router.route("what time is it")
    assert result is not None, "Should match time query"
    assert result["type"] == "chat", "Time query should be chat"
    assert ":" in result["response"], "Should include time"
    print("✓ Time query works")
    
    # Test date query
    result = router.route("what is the date")
    assert result is not None, "Should match date query"
    assert result["type"] == "chat", "Date query should be chat"
    assert "20" in result["response"], "Should include year"
    print("✓ Date query works")
    
    # Test open app
    result = router.route("open chrome")
    assert result is not None, "Should match open app"
    assert result["type"] == "plan", "Open app should be plan"
    assert result["steps"][0]["tool"] == "open_app", "Should use open_app tool"
    print("✓ Open app detection works")
    
    # Test open website with browser
    result = router.route("open youtube in brave")
    assert result is not None, "Should match website+browser"
    assert result["type"] == "plan", "Should be plan"
    assert "youtube" in result["steps"][0]["args"]["url"], "Should include youtube"
    assert result["steps"][0]["args"]["browser"] == "brave", "Should include brave"
    print("✓ Open website in browser works")
    
    # Test open website without browser
    result = router.route("open google.com")
    assert result is not None, "Should match website"
    assert result["type"] == "plan", "Should be plan"
    assert "google" in result["steps"][0]["args"]["url"], "Should include google"
    print("✓ Open website without browser works")
    
    # Test help
    result = router.route("help")
    assert result is not None, "Should match help"
    assert result["type"] == "chat", "Help should be chat"
    assert "can help" in result["response"].lower(), "Should mention capabilities"
    print("✓ Help matches")
    
    # Test thank you
    result = router.route("thank you")
    assert result is not None, "Should match thank you"
    assert result["type"] == "chat", "Thank you should be chat"
    print("✓ Thank you matches")
    
    # Test no match
    result = router.route("calculate the meaning of life")
    assert result is None, "Should not match unknown query"
    print("✓ Unknown queries pass through to LLM")


async def test_agent_router_local():
    """Test AgentRouter with LocalRouter."""
    print("\n=== Test 2: AgentRouter Local Fallback ===")
    
    router = AgentRouter()
    
    # Test local greeting (chat intent)
    result = await router.route("hello there")
    assert result["type"] == "response", "Greeting should be response"
    assert "Hello" in result["response"], "Should contain greeting"
    print("✓ Local greeting works via router")
    
    # Test local command (open app)
    result = await router.route("open chrome")
    assert result["type"] == "execution", "Open app should execute"
    print("✓ Local command execution works")
    
    # Test local time query
    result = await router.route("what time is it")
    assert result["type"] == "response", "Time should be response"
    assert ":" in result["response"], "Should include time"
    print("✓ Local time query works")


async def test_offline_capability():
    """Verify Jarvis works without LLM."""
    print("\n=== Test 3: Offline Capability ===")
    
    router = LocalRouter()
    
    # Simulate common user intents that should work offline
    test_cases = [
        ("Hi", True, "greeting"),
        ("what time is it", True, "time query"),
        ("open chrome", True, "app launch"),
        ("thanks", True, "thank you"),
        ("help", True, "help request"),
        ("open google in firefox", True, "website+browser"),
        ("what's today", True, "date query"),
        ("bye", True, "farewell"),
    ]
    
    success_count = 0
    for text, should_match, desc in test_cases:
        result = router.route(text)
        if should_match:
            assert result is not None, f"Should match: {desc}"
            success_count += 1
            print(f"✓ {desc}: '{text}'")
        else:
            assert result is None, f"Should not match: {desc}"
            success_count += 1
    
    print(f"\n✓ {success_count}/{len(test_cases)} offline intents work")


async def run_all_tests():
    """Run all tests."""
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║ Local Fallback Execution Layer - Tests                 ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    await test_local_router()
    await test_agent_router_local()
    await test_offline_capability()
    
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║ ✓ All tests passed! Offline mode verified.             ║")
    print("╚════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
