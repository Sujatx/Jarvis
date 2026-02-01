import os
import json
import tempfile

def load_json(path) -> dict:
    """Returns {} on missing or parse error."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_json(path, data) -> None:
    """Atomic: write to temp then os.replace."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp_path, path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e

def update_json(path, key, value) -> None:
    """Loads, sets key=value, then save_json."""
    data = load_json(path)
    data[key] = value
    save_json(path, data)

def ensure_json(path, default_dict) -> dict:
    """Creates file with default if missing and returns current content."""
    if not os.path.exists(path):
        save_json(path, default_dict)
        return default_dict
    return load_json(path)

def get_env_value(path, key) -> str:
    """Reads a value from .env file manually to avoid cache issues."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""

def set_env_value(path, key, value) -> None:
    """Atomic write/update for .env file."""
    lines = []
    found = False
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f'{key}="{value}"\n')
                    found = True
                else:
                    lines.append(line)
    
    if not found:
        lines.append(f'{key}="{value}"\n')
        
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(tmp_path, path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e
