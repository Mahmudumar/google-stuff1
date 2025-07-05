import os
import sqlite3
import datetime
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/tasks']
DB_FILE = 'tasks.db'
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'

# --- AUTHENTICATION ---


def get_google_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

# --- DATABASE ---


def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, list_name TEXT NOT NULL,
            due_time TEXT, notes TEXT, status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def show_all_tasks_from_db():
    """Reads all tasks from the local database and prints them."""
    print("\n--- Here are all your active tasks, boss ---")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY list_name, due_time ASC")
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        print("No active tasks found. Looks like a clear board!")
        return

    current_list = None
    for task in tasks:
        if task['list_name'] != current_list:
            current_list = task['list_name']
            print(f"\n[ {current_list.upper()} ]")

        due_date_str = "(No due date)"
        if task['due_time']:
            due_date = datetime.datetime.fromisoformat(
                task['due_time'].replace('Z', '+00:00'))
            due_date_str = f"(Due: {due_date.strftime('%a, %b %d')})"

        print(f"  - {task['title']} {due_date_str}")

def show_todays_tasks_from_db():
    """Returns today's tasks as a string message for notification."""
    msg = ""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM tasks WHERE due_time IS NOT NULL AND DATE(due_time) <= DATE('now') ORDER BY due_time ASC"
    cursor.execute(query)
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        return "🎉 Nothing pressing is due today."

    for task in tasks:
        due_date = datetime.datetime.fromisoformat(
            task['due_time'].replace('Z', '+00:00'))

        status = "[OVERDUE]" if due_date.date() < datetime.date.today() else "[TODAY]"
        msg += f"{status:<10} {task['title']} (From: {task['list_name']})\n"

    return msg.strip()


# --- SYNC TASKS FROM GOOGLE TO SQLITE ---

def sync_tasks_to_db(creds):
    print("Upchups is syncing with your Google Tasks...")
    try:
        service = build('tasks', 'v1', credentials=creds)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Step 1: Push local-only tasks to Google
        cursor.execute("SELECT * FROM tasks WHERE id LIKE 'local-%'")
        local_tasks = cursor.fetchall()
        tasklists = service.tasklists().list().execute().get('items', [])
        default_list_id = tasklists[0]['id'] if tasklists else None

        for task in local_tasks:
            task_dict = {
                'title': task[1],
                'notes': task[4] or '',
                'status': task[5]
            }
            if task[3]:
                task_dict['due'] = task[3]

            new_task = service.tasks().insert(
                tasklist=default_list_id, body=task_dict).execute()

            # Update the task ID in the DB
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task[0],))
            cursor.execute(
                '''INSERT INTO tasks (id, title, list_name, due_time, notes, status)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (new_task['id'], new_task['title'], task[2], new_task.get(
                    'due'), new_task.get('notes'), new_task['status'])
            )
            print(f"Pushed task to Google: {new_task['title']}")

        conn.commit()

        # Step 2: Sync all active tasks from Google
        cursor.execute('DELETE FROM tasks')
        task_lists = service.tasklists().list().execute().get('items', [])
        total_tasks_synced = 0
        for task_list in task_lists:
            list_name = task_list['title']
            tasks_result = service.tasks().list(
                tasklist=task_list['id'], showCompleted=False).execute()
            for task in tasks_result.get('items', []):
                cursor.execute(
                    '''REPLACE INTO tasks (id, title, list_name, due_time, notes, status)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (task['id'], task['title'], list_name, task.get(
                        'due'), task.get('notes'), task['status'])
                )
                total_tasks_synced += 1

        conn.commit()
        conn.close()
        print(f"Sync complete. Found {total_tasks_synced} active tasks.")

    except HttpError as err:
        print(f"An API error occurred: {err}")
    except sqlite3.Error as db_err:
        print("Database error:", db_err)
    except Exception as e:
        print("Unexpected error:", e)

# --- ADD TASK ---


def add_task():
    title = input("Enter task title: ").strip()
    if not title:
        print("Task title cannot be empty.")
        return
    list_name = input(
        "Enter list name (default: My Tasks): ").strip() or "My Tasks"
    due_date = input("Enter due date (YYYY-MM-DD) [optional]: ").strip()
    notes = input("Enter notes [optional]: ").strip()

    due_time = None
    if due_date:
        try:
            due_time = datetime.datetime.strptime(
                due_date, "%Y-%m-%d").isoformat() + 'Z'
        except ValueError:
            print("Invalid date format. Skipping due date.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    task_id = f"local-{datetime.datetime.now().timestamp()}"
    cursor.execute(
        '''INSERT INTO tasks (id, title, list_name, due_time, notes, status)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (task_id, title, list_name, due_time, notes, 'needsAction')
    )
    conn.commit()
    conn.close()
    print("Task added locally.")

# --- MARK TASK DONE ---


def mark_task_done():
    title = input(
        "Enter the exact title of the task to mark as done: ").strip()
    if not title:
        print("Title cannot be empty.")
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'completed' WHERE title = ?", (title,))
    if cursor.rowcount > 0:
        print("Task marked as completed.")
    else:
        print("No matching task found.")
    conn.commit()
    conn.close()

# --- DELETE TASK ---


def delete_task():
    title = input("Enter the exact title of the task to delete: ").strip()
    if not title:
        print("Title cannot be empty.")
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE title = ?", (title,))
    if cursor.rowcount > 0:
        print("Task deleted.")
    else:
        print("No matching task found.")
    conn.commit()
    conn.close()

# --- CLI ENTRY POINT ---

def main2():
    while True:
        print("\nWelcome to Upchups! Type 'help' for commands or 'exit' to quit.")
        print("Type 'help' for a list of commands.")
        command = input("> ").strip().lower()

        if command == 'sync':
            creds = get_google_credentials()
            sync_tasks_to_db(creds)
        elif command == 'add':
            add_task()
        elif command == 'all':
            show_all_tasks_from_db()
        elif command == 'today':
            show_todays_tasks_from_db()
        elif command == 'done':
            mark_task_done()
        elif command == 'delete':
            delete_task()
        elif command == 'exit':
            sys.exit(0)
        elif command == 'help':
            print("\nAvailable commands:")
            print("  sync     - Sync local and Google Tasks")
            print("  all      - List all tasks")
            print("  add      - Add a new task")
            print("  done     - Mark a task as completed")
            print("  delete   - Delete a task")
            print("  help     - Show this help message")
            print("  exit     - Exit the program")
        else:
            print(f"Unknown command: {command}. Type 'help' for options.")


def main():
    initialize_database()
    if len(sys.argv) < 2:
        main2()
        return

    command = sys.argv[1].lower()

    if command == 'sync':
        creds = get_google_credentials()
        sync_tasks_to_db(creds)
    elif command == 'add':
        add_task()
    elif command == 'all':
        show_all_tasks_from_db()
    elif command == 'today':
        show_todays_tasks_from_db()
    elif command == 'done':
        mark_task_done()
    elif command == 'delete':
        delete_task()
    elif command == 'exit':
        sys.exit(0)

    elif command == 'help':
        print("\nAvailable commands:")
        print("  sync     - Sync local and Google Tasks")
        print("  all      - List all tasks")
        print("  add      - Add a new task")
        print("  done     - Mark a task as completed")
        print("  delete   - Delete a task")
        print("  help     - Show this help message")
        print("  exit    - Exit the program")
    else:
        print(f"Unknown command: {command}. Type 'help' for options.")


if __name__ == '__main__':
    main()
