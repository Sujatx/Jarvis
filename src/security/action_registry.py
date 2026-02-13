ACTION_REGISTRY = {
    "open_app": {
        "risk": "low",
        "confirm": False
    },
    "close_app": {
        "risk": "medium",
        "confirm": False
    },
    "open_website": {
        "risk": "low",
        "confirm": False
    },
    "system_time": {
        "risk": "low",
        "confirm": False
    },
    "system_date": {
        "risk": "low",
        "confirm": False
    },
    "shutdown_system": {
        "risk": "critical",
        "confirm": True
    },
    "delete_file": {
        "risk": "critical",
        "confirm": True
    },
    "add_task": {
        "risk": "low",
        "confirm": False
    },
    "list_tasks": {
        "risk": "low",
        "confirm": False
    },
    "add_calendar_event": {
        "risk": "low",
        "confirm": False
    }
}
