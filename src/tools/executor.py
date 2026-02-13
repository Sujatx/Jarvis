from src.tools import registry

async def execute(name, args):
    """Fetch tool from registry and execute it with provided arguments"""
    tool = registry.get(name)
    if not tool:
        return {"error": "tool_not_found"}
    
    try:
        return await tool.execute(**args)
    except Exception as e:
        return {"error": "execution_failed", "details": str(e)}
