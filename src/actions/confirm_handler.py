from src.core.pending_action_store import STORE
import asyncio

async def confirm(action_router):
    """Confirm and execute the pending action"""
    intent = STORE.get()
    if not intent:
        return {"status": "nothing_pending", "message": "There are no pending actions to confirm, sir."}

    # Execute using the router's core execution logic
    result = await action_router.execute(intent)
    STORE.clear()
    return result
