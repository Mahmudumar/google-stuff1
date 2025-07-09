"""We want to create an app that just allows us to see our tasks
while we are offline. Simple. No fancy features yet. not even memory 
nor notifier. I just wanna sync my tasks with my laptop and be able
to do that while offline. When online, then it can take my local 
database to my account and i will see it on my phone. 

We can then call it a finished project because all i wanted was a todo list app of my own
synced to my google account. not even a personal assistant. Not yet.

Just sync google tasks. Just be clear."""
import uuid
import sqlite3
import os


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ['https://www.googleapis.com/auth/tasks']
DB_FILE = 'tasks.db'
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'


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


def get_all_task_lists():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT list_name FROM tasks')
    lists = [row[0] for row in cursor.fetchall()]
    conn.close()
    return lists


def get_tasks_online(creds, show_completed=False):
    service = build('tasks', 'v1', credentials=creds)
    all_tasks = []

    try:
        tasklists = service.tasklists().list().execute().get('items', [])
        if not tasklists:
            print("No task lists found.")
            return []

        for tl in tasklists:
            list_id = tl['id']
            list_name = tl['title']
            # print(f"\nTask List: {list_name}")

            tasks_result = service.tasks().list(
                tasklist=list_id,
                showCompleted=show_completed
            ).execute()

            tasks = tasks_result.get('items', [])
            if not tasks:
                # print("  (No tasks)")
                continue

            for task in tasks:
                task_info = {
                    'id': task.get('id'),
                    'title': task.get('title', '[No title]'),
                    'due': task.get('due', 'No due date'),
                    'status': task.get('status'),
                    'notes': task.get('notes', ''),
                    'list_name': list_name
                }

                # print(
                #     f"  - {task_info['title']} | Due: {task_info['due']} | Status: {task_info['status']}")
                all_tasks.append(task_info)

        return all_tasks

    except Exception as e:
        print("Error fetching tasks from Google:", e)
        return []


def insert_task_to_db(task):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        REPLACE INTO tasks (id, title, list_name, due_time, notes, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        task['id'],
        task['title'],
        task['list_name'],
        task['due'],
        task['notes'],
        task['status']
    ))

    conn.commit()
    conn.close()
    print(f"✅ Inserted: {task['title']} into DB")


def add_local_task(title, list_name='Tasks', due_time=None, notes='', status='needsAction'):
    local_id = f'local-{uuid.uuid4().hex[:8]}'

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (id, title, list_name, due_time, notes, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (local_id, title, list_name, due_time, notes, status))

    conn.commit()
    conn.close()
    print(f"📝 Saved locally: {title}")


def delete_local_task(task_id):
    """permanently delete a task from the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    print(f"🗑️ Deleted task with ID: {task_id}")


def delete_syncable_task(task_id):
    """Mark a task as deleted, so that
    when we are syncing, we perform this action
    in the API to remove this task if it is in
    the account but deleted here, in the local db"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()


def get_all_local_tasks():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks')
    tasks = cursor.fetchall()
    conn.close()
    return tasks


def get_task_by_id(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    return task


def update_local_task(task_id, title=None, list_name=None, due_time=None, notes=None, status=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if list_name is not None:
        updates.append("list_name = ?")
        params.append(list_name)
    if due_time is not None:
        updates.append("due_time = ?")
        params.append(due_time)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if status is not None:
        updates.append("status = ?")
        params.append(status)

    if updates:
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        params.append(task_id)
        cursor.execute(query, tuple(params))
        conn.commit()
        print(f"🔄 Updated task with ID: {task_id}")

    conn.close()


def update_google_tasks_from_local(creds):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM tasks WHERE id NOT LIKE 'local-%' AND status = 'completed'")
    completed_tasks = cursor.fetchall()

    if not completed_tasks:
        print("✅ No completed tasks to update online.")
        conn.close()
        return

    service = build('tasks', 'v1', credentials=creds)
    tasklists = service.tasklists().list().execute().get('items', [])
    tasklist_map = {tl['title']: tl['id'] for tl in tasklists}

    for task in completed_tasks:
        task_id, title, list_name, due, notes, status = task

        # Skip invalid or local tasks
        if not task_id or task_id.startswith('local-'):
            print(f"⚠️ Skipping invalid task ID: {task_id}")
            continue

        list_id = tasklist_map.get(list_name)
        if not list_id:
            print(
                f"⚠️ List not found for '{title}' (list_name='{list_name}'), skipping...")
            continue

        try:
            service.tasks().update(
                tasklist=list_id,
                task=task_id,
                body={'status': 'completed'}
            ).execute()
            print(f"☑️ Updated on Google: {title}")
        except Exception as e:
            print(f"❌ Failed to update task '{title}' – {e}")

    conn.close()


def push_local_tasks_to_google(creds):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id LIKE 'local-%'")
    local_tasks = cursor.fetchall()

    if not local_tasks:
        print("✅ No local tasks to push.")
        conn.close()
        return

    service = build('tasks', 'v1', credentials=creds)
    tasklists = service.tasklists().list().execute().get('items', [])
    tasklist_map = {tl['title']: tl['id'] for tl in tasklists}
    default_list_id = tasklists[0]['id'] if tasklists else None

    for task in local_tasks:
        local_id, title, list_name, due_time, notes, status = task

        task_body = {
            'title': title,
            'notes': notes,
            'status': status
        }
        if due_time:
            task_body['due'] = due_time

        list_id = tasklist_map.get(list_name, default_list_id)

        try:
            new_task = service.tasks().insert(tasklist=list_id, body=task_body).execute()

            # Safely replace the local task only if insert succeeded
            cursor.execute("BEGIN")
            cursor.execute("DELETE FROM tasks WHERE id = ?", (local_id,))
            cursor.execute('''
                INSERT INTO tasks (id, title, list_name, due_time, notes, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                new_task['id'],
                new_task['title'],
                list_name,
                new_task.get('due'),
                new_task.get('notes'),
                new_task['status']
            ))
            conn.commit()
            print(f"☁️ Pushed: {title} → Google")

        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to push '{title}' — {e}")

    conn.close()
    print("🚀 Done pushing all local tasks.")


def mark_task_as_completed(task_id, creds):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()

    if not task_id or task_id.startswith('local-'):
        print(f"⚠️ Skipping invalid task ID: {task_id}")
        conn.close()
        return  # ✅ <-- this line was missing

    service = build('tasks', 'v1', credentials=creds)
    try:
        service.tasks().update(
            tasklist=task[2],  # list_name
            task=task_id,
            body={'status': 'completed'}
        ).execute()
        cursor.execute('UPDATE tasks SET status = ? WHERE id = ?',
                       ('completed', task_id))
        conn.commit()
        print(f"✅ Marked task '{task[1]}' as completed.")
    except HttpError as e:
        print(f"❌ Error marking task as completed: {e}")

    conn.close()


if __name__ == "__main__":
    # run when connected to the internet
    creds = get_google_credentials()
    initialize_database()
    all_tasks = get_tasks_online(creds)

    for task in all_tasks:
        insert_task_to_db(task)
    print("✅ All tasks fetched and stored locally.")

    add_local_task("Sample Task", "Personal",
                   "2023-12-31T23:59:59Z", "This is a sample task.")
    print("📝 Added a sample local task.")
