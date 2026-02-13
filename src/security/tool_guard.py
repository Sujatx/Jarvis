from src.tools import registry

def validate(tool_name, args) -> (bool, str):
    """
    Validate tool call:
    - Tool must be registered
    - Args must be a dictionary
    - Args cannot contain nested objects
    - Arg value length must be <= 500 characters
    """
    tool = registry.get(tool_name)
    if not tool:
        return False, "tool_not_found"
    
    if not isinstance(args, dict):
        return False, "invalid_arguments_format"
    
    for key, value in args.items():
        if isinstance(value, (dict, list)):
            return False, f"nested_argument_rejected: {key}"
        
        if len(str(value)) > 500:
            return False, f"argument_too_long: {key}"
            
    return True, "valid"
