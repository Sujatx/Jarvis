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
