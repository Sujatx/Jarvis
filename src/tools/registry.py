TOOLS = {}

def register(tool_cls):
    """Register a tool class instance"""
    instance = tool_cls()
    TOOLS[instance.name] = instance

def get(name):
    """Retrieve a tool instance by name"""
    return TOOLS.get(name)

def get_tool(name):
    """Retrieve a tool instance by name (alias for get)"""
    return TOOLS.get(name)

def list_schemas():
    """Return a list of all registered tool schemas"""
    return [t.schema for t in TOOLS.values()]

def get_schemas():
    """Alias for list_schemas for API consistency"""
    return list_schemas()
