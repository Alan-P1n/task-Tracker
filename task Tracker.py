#!/usr/bin/env python3
"""
Simple task CLI that persists tasks to tasks.json.

Usage examples:
  task-cli.py add "Buy groceries"
  task-cli.py update 1 "Buy groceries and cook dinner"
  task-cli.py delete 1
  task-cli.py mark-in-progress 1
  task-cli.py mark-done 1
  task-cli.py list
  task-cli.py list done
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

TASKS_FILE = os.path.join(os.path.expanduser("~"), ".task_cli_tasks.json")
VALID_STATUSES = ("todo", "in-progress", "done")


def load_tasks() -> List[Dict]:
    """Load tasks from JSON file. Return empty list if file doesn't exist or is invalid."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        # If file is corrupted, don't crash — return empty list (or you could back it up).
        print("Warning: couldn't read tasks file; starting with an empty list.", file=sys.stderr)
    return []


def save_tasks(tasks: List[Dict]) -> None:
    """Save tasks to JSON file (atomic write)."""
    tmp = TASKS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    os.replace(tmp, TASKS_FILE)


def next_id(tasks: List[Dict]) -> int:
    """Return next integer ID for a new task."""
    if not tasks:
        return 1
    return max(int(t.get("id", 0)) for t in tasks) + 1


def add_task(title: str) -> Dict:
    tasks = load_tasks()
    tid = next_id(tasks)
    task = {
        "id": tid,
        "title": title,
        "status": "todo",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def find_task(tasks: List[Dict], tid: int) -> Optional[Dict]:
    for t in tasks:
        if int(t.get("id")) == tid:
            return t
    return None


def update_task(tid: int, new_title: str) -> bool:
    tasks = load_tasks()
    t = find_task(tasks, tid)
    if not t:
        return False
    t["title"] = new_title
    t["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_tasks(tasks)
    return True


def delete_task(tid: int) -> bool:
    tasks = load_tasks()
    orig_len = len(tasks)
    tasks = [t for t in tasks if int(t.get("id")) != tid]
    if len(tasks) == orig_len:
        return False
    save_tasks(tasks)
    return True


def set_status(tid: int, status: str) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status")
    tasks = load_tasks()
    t = find_task(tasks, tid)
    if not t:
        return False
    t["status"] = status
    t["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_tasks(tasks)
    return True


def list_tasks(status: Optional[str] = None) -> List[Dict]:
    tasks = load_tasks()
    if status:
        if status not in VALID_STATUSES:
            raise ValueError("Invalid status for listing")
        tasks = [t for t in tasks if t.get("status") == status]
    # sort by id
    tasks_sorted = sorted(tasks, key=lambda x: int(x.get("id", 0)))
    return tasks_sorted


def pretty_print_tasks(tasks: List[Dict]) -> None:
    if not tasks:
        print("No tasks found.")
        return
    for t in tasks:
        print(f"[{t['id']}] ({t['status']}) {t['title']}")


def main():
    parser = argparse.ArgumentParser(prog="task-cli.py", description="Simple task CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a new task")
    p_add.add_argument("title", help="Task title", nargs="+")  # accept multi-word

    # update
    p_upd = sub.add_parser("update", help="Update a task's title")
    p_upd.add_argument("id", type=int, help="Task ID")
    p_upd.add_argument("title", nargs="+", help="New title")

    # delete
    p_del = sub.add_parser("delete", help="Delete a task by ID")
    p_del.add_argument("id", type=int, help="Task ID")

    # mark-in-progress
    p_mip = sub.add_parser("mark-in-progress", help="Mark a task as in-progress")
    p_mip.add_argument("id", type=int, help="Task ID")

    # mark-done
    p_md = sub.add_parser("mark-done", help="Mark a task as done")
    p_md.add_argument("id", type=int, help="Task ID")

    # list
    p_list = sub.add_parser("list", help="List tasks (optionally by status)")
    p_list.add_argument("status", nargs="?", choices=VALID_STATUSES, help="Optional status filter")

    args = parser.parse_args()

    try:
        if args.cmd == "add":
            title = " ".join(args.title).strip()
            if not title:
                print("Error: title cannot be empty.", file=sys.stderr)
                sys.exit(1)
            task = add_task(title)
            print(f"Task added successfully (ID: {task['id']})")

        elif args.cmd == "update":
            title = " ".join(args.title).strip()
            if not title:
                print("Error: title cannot be empty.", file=sys.stderr)
                sys.exit(1)
            ok = update_task(args.id, title)
            if ok:
                print(f"Task {args.id} updated.")
            else:
                print(f"Task {args.id} not found.", file=sys.stderr)
                sys.exit(2)

        elif args.cmd == "delete":
            ok = delete_task(args.id)
            if ok:
                print(f"Task {args.id} deleted.")
            else:
                print(f"Task {args.id} not found.", file=sys.stderr)
                sys.exit(2)

        elif args.cmd == "mark-in-progress":
            ok = set_status(args.id, "in-progress")
            if ok:
                print(f"Task {args.id} marked as in-progress.")
            else:
                print(f"Task {args.id} not found.", file=sys.stderr)
                sys.exit(2)

        elif args.cmd == "mark-done":
            ok = set_status(args.id, "done")
            if ok:
                print(f"Task {args.id} marked as done.")
            else:
                print(f"Task {args.id} not found.", file=sys.stderr)
                sys.exit(2)

        elif args.cmd == "list":
            tasks = list_tasks(args.status)
            pretty_print_tasks(tasks)

        else:
            parser.print_help()

    except ValueError as ve:
        print("Error:", ve, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
