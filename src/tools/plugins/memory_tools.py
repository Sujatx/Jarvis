"""
Memory Tools - Plugins for interacting with persistent memory (Tasks & Calendar).
"""

from src.tools.base_tool import BaseTool
from src.tools.registry import register
from src.core.memory.repositories import TaskRepository, CalendarRepository

class AddTaskTool(BaseTool):
    name = "add_task"
    description = "Add a new task to the to-do list"
    schema = {
        "name": "add_task",
        "description": "Add a new task to the to-do list",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The task description"},
                "priority": {"type": "integer", "description": "Priority level (1-5)"}
            },
            "required": ["content"]
        }
    }

    async def execute(self, **kwargs) -> dict:
        content = kwargs.get("content")
        priority = kwargs.get("priority", 1)
        
        if not content:
            return {"status": "error", "message": "Content is required"}
            
        repo = TaskRepository()
        task_id = repo.add_task(content, priority=priority)
        return {"status": "success", "message": f"Task added: {content}", "task_id": task_id}

class ListTasksTool(BaseTool):
    name = "list_tasks"
    description = "List pending tasks"
    schema = {
        "name": "list_tasks",
        "description": "List all pending tasks",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }

    async def execute(self, **kwargs) -> dict:
        repo = TaskRepository()
        tasks = repo.list_tasks()
        
        if not tasks:
            return {"status": "success", "message": "You have no pending tasks, sir."}
            
        task_list = "\n".join([f"- {t['content']}" for t in tasks])
        return {"status": "success", "message": f"Here are your tasks:\n{task_list}"}

class AddEventTool(BaseTool):
    name = "add_calendar_event"
    description = "Add an event to the calendar"
    schema = {
        "name": "add_calendar_event",
        "description": "Add an event to the calendar",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "start_time": {"type": "string", "description": "Start time (YYYY-MM-DD HH:MM:SS)"},
                "location": {"type": "string", "description": "Location (optional)"}
            },
            "required": ["title", "start_time"]
        }
    }

    async def execute(self, **kwargs) -> dict:
        title = kwargs.get("title")
        start_time = kwargs.get("start_time")
        location = kwargs.get("location")
        
        repo = CalendarRepository()
        try:
            repo.add_event(title, start_time, location=location)
            return {"status": "success", "message": f"Event '{title}' scheduled for {start_time}."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to add event: {str(e)}"}

# Register tools
register(AddTaskTool)
register(ListTasksTool)
register(AddEventTool)
