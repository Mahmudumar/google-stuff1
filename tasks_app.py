"""We want to create an app that just allows us to see our tasks
while we are offline. Simple. No fancy features yet. not even memory 
nor notifier. I just wanna sync my tasks with my laptop and be able
to do that while offline. When online, then it can take my local 
database to my account and i will see it on my phone. 

We can then call it a finished project because all i wanted was a todo list app of my own
synced to my google account. not even a personal assistant. Not yet.

Just sync google tasks. Just be clear."""
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
            print(f"\nTask List: {list_name}")

            tasks_result = service.tasks().list(
                tasklist=list_id,
                showCompleted=show_completed
            ).execute()

            tasks = tasks_result.get('items', [])
            if not tasks:
                print("  (No tasks)")
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

                print(
                    f"  - {task_info['title']} | Due: {task_info['due']} | Status: {task_info['status']}")
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




all_tasks = get_tasks_online(get_google_credentials())

for task in all_tasks:
    insert_task_to_db(task)

