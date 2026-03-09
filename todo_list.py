"""A simple command-line TODO list manager."""

import json
import os
from datetime import datetime


DATA_FILE = "todos.json"


def load_todos():
    """Load todos from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_todos(todos):
    """Save todos to the JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(todos, f, indent=2)


def add_todo(title, priority="medium"):
    """Add a new TODO item."""
    todos = load_todos()
    todo = {
        "id": len(todos) + 1,
        "title": title,
        "priority": priority,
        "done": False,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    todos.append(todo)
    save_todos(todos)
    return todo


def complete_todo(todo_id):
    """Mark a TODO item as complete."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = True
            todo["completed_at"] = datetime.now().isoformat()
            save_todos(todos)
            return todo
    return None


def delete_todo(todo_id):
    """Delete a TODO item by ID."""
    todos = load_todos()
    # TODO: instead of deleting immediately, soft-delete by adding a deleted_at field
    todos = [t for t in todos if t["id"] != todo_id]
    save_todos(todos)


def list_todos(show_done=False):
    """Return the list of TODO items."""
    todos = load_todos()
    if not show_done:
        todos = [t for t in todos if not t["done"]]
    return todos


def get_stats():
    """Return stats about the TODO list."""
    todos = load_todos()
    total = len(todos)
    done = sum(1 for t in todos if t["done"])
    by_priority = {}
    for todo in todos:
        p = todo.get("priority", "medium")
        by_priority.setdefault(p, {"total": 0, "done": 0})
        by_priority[p]["total"] += 1
        if todo["done"]:
            by_priority[p]["done"] += 1
    return {"total": total, "done": done, "pending": total - done, "by_priority": by_priority}


def search_todos(query):
    """Search todos by title (case-insensitive)."""
    todos = load_todos()
    return [t for t in todos if query.lower() in t["title"].lower()]
