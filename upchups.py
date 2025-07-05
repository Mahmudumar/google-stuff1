import os.path
import sqlite3
import datetime
import sys # We need this library to read command-line arguments

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/tasks.readonly']
DB_FILE = 'tasks.db'

# --- The functions for authentication, database setup, and syncing are THE SAME ---
# (I've collapsed them here for brevity, but they should be in your file)

def get_google_credentials():
    # ... (same code as before) ...
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def initialize_database():
    # ... (same code as before) ...
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

def sync_tasks_to_db(creds):
    # ... (same code as before) ...
    print("Upchups is syncing with your Google Tasks...")
    try:
        service = build('tasks', 'v1', credentials=creds)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks')
        task_lists = service.tasklists().list().execute().get('items', [])
        total_tasks_synced = 0
        for task_list in task_lists:
            list_name = task_list['title']
            tasks_result = service.tasks().list(tasklist=task_list['id'], showCompleted=False).execute()
            for task in tasks_result.get('items', []):
                cursor.execute(
                    '''REPLACE INTO tasks (id, title, list_name, due_time, notes, status)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (task['id'], task['title'], list_name, task.get('due'), task.get('notes'), task['status'])
                )
                total_tasks_synced += 1
        conn.commit()
        conn.close()
        print(f"Sync complete. Found {total_tasks_synced} active tasks.")
    except HttpError as err:
        print(f"An API error occurred: {err}")

# --- NEW AND IMPROVED "ANSWER" FUNCTIONS ---

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
            due_date = datetime.datetime.fromisoformat(task['due_time'].replace('Z', '+00:00'))
            due_date_str = f"(Due: {due_date.strftime('%a, %b %d')})"
        
        print(f"  - {task['title']} {due_date_str}")

def show_todays_tasks_from_db():
    """This is Upchups's core "answer" function."""
    print("\n--- Let's see what's on your plate for today... ---")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # The SQL query is the magic here. It gets tasks that are due today OR are overdue.
    # DATE('now') gets today's date in SQLite.
    query = "SELECT * FROM tasks WHERE due_time IS NOT NULL AND DATE(due_time) <= DATE('now') ORDER BY due_time ASC"
    cursor.execute(query)
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        print("Nothing pressing is due today. Enjoy the clear schedule!")
        return
    
    print("Here is your briefing:")
    for task in tasks:
        due_date = datetime.datetime.fromisoformat(task['due_time'].replace('Z', '+00:00'))
        
        # Add a visual cue for overdue tasks
        if due_date.date() < datetime.date.today():
            status = "[OVERDUE]"
        else:
            status = "[TODAY]"

        print(f"  {status:<10} {task['title']} (From: {task['list_name']})")

def print_help():
    """Prints the help message for Upchups."""
    print("\nHello, I'm Upchups, your personal task assistant.")
    print("You can ask me to do things like this:")
    print("  python upchups.py sync      - Get the latest tasks from Google.")
    print("  python upchups.py today     - Show tasks that are due today or are overdue.")
    print("  python upchups.py all       - Show all of your active tasks.")

# --- THE NEW MAIN LOGIC ---
def main():
    """The main entry point for the Upchups assistant."""
    initialize_database()

    # sys.argv is a list of words typed on the command line.
    # sys.argv[0] is the script name itself ('upchups.py')
    # sys.argv[1] would be the first command (e.g., 'sync')
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower() # .lower() makes it case-insensitive

    if command == 'sync':
        creds = get_google_credentials()
        sync_tasks_to_db(creds)
    elif command == 'today':
        show_todays_tasks_from_db()
    elif command == 'all':
        show_all_tasks_from_db()
    else:
        print(f"\nSorry, I don't understand the command '{command}'.")
        print_help()


if __name__ == '__main__':
    main()