# GUI.py
"""
This is a customtkinter GUI frontend for your offline Google Tasks sync tool.
It allows you to:
- View all local tasks with checkboxes
- Add a local task
- Push local tasks to Google
- Sync from Google to local DB
- Sync completed local tasks back to Google

You must have the main sync logic available in a separate file (e.g., core.py).
"""

import customtkinter as ctk
from tkinter import messagebox
from core import (
    get_google_credentials, initialize_database, get_all_local_tasks,
    add_local_task, push_local_tasks_to_google, get_tasks_online,
    insert_task_to_db, update_local_task, update_google_tasks_from_local,
    delete_local_task, get_task_by_id
)

ctk.set_appearance_mode("System")  # Light, Dark, or System
ctk.set_default_color_theme("green")  # You can change the theme


class app:
    """offline default app"""
    dark_grey = "#333333"
    black = "#000000"
    blue = "#4d65ff"
    red = "#e41b1b"
    green = "green"

    def __init__(self, master: ctk.CTk):
        self.master = master
        self.master.title("📝 BobsiMo")
        self.master.geometry("700x500")

        try:
            self.creds = get_google_credentials()
        except Exception as e:
            self.creds = None

    def framing(self):
        # Create scrollable frame for tasks
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.master, width=480, height=400)
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(self.master)
        btn_frame.pack(pady=5)

        ctk.CTkButton(btn_frame, text="🔄 Sync from Google",
                      command=self.sync_from_google).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="☁️ Push to Google",
                      command=self.push_to_google).grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frame, text="➕ Add Local Task",
                      command=self.add_task).grid(row=0, column=2, padx=5)
        ctk.CTkButton(btn_frame, text="🔁 Refresh", command=self.refresh).grid(
            row=0, column=3, padx=5)

        initialize_database()
        self.refresh()

    def refresh(self):
        """Refresh the UI with all tasks in the DB"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        tasks = get_all_local_tasks()
        for task in tasks:
            task_id, title, list_name, due, notes, status = task
            self._make_task_bt(task_id, title, list_name, due, notes, status)

    def _make_task_bt(self, task_id, title, list_name, due, notes, status):
        cb_frame = ctk.CTkFrame(self.scrollable_frame)

        cb_frame.pack(anchor='w', pady=4, padx=8, expand=1, fill="x")
        var = ctk.BooleanVar(value=(status == 'completed'))
        cb = ctk.CTkCheckBox(
            cb_frame,
            text=title,
            variable=var,
            command=lambda tid=task_id, v=var: self.toggle_task_complete(
                tid, v),
            font=("Segoe UI", 14),
            checkbox_height=25,
            checkbox_width=25,
            height=40,
            width=440,
            corner_radius=6
        )
        cb.pack(side="left")

        del_task_bt = ctk.CTkButton(
            cb_frame, width=20,
            text="Delete", fg_color=self.dark_grey, hover_color=self.red,
            command=lambda
            tid=task_id: self.delete_task(task_id=tid))

        del_task_bt.pack(side="right", padx=10)

        edit_task_bt = ctk.CTkButton(
            cb_frame, width=20,
            text="Edit",
            fg_color=self.dark_grey, hover_color=self.blue,
            command=lambda
            tid=task_id: self.edit_task_win(task_id=tid))

        edit_task_bt.pack(side="right",)

    def toggle_task_complete(self, task_id, var):
        new_status = 'completed' if var.get() else 'needsAction'
        update_local_task(task_id, status=new_status)
        print(f"Task {task_id} status updated to {new_status}")

    def task_maker_win(self, edit=False, task_id=None, title=None,
                       list_name=None,
                       due=None,
                       notes=None,
                       status=None):
        """return title, list_name,
          due_time, notes, status

          of the task just created"""

        self.act_win = ctk.CTkToplevel()
        self.act_win.tkraise()
        self.act_win.wm_title("Add Task")
        self.act_win.geometry("400x350+500+250")
        self.act_win.transient(self.master)

        form_frame = ctk.CTkFrame(self.act_win)
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Title
        ctk.CTkLabel(form_frame, text="Title:*").grid(
            row=0, column=0, sticky="w", pady=5)
        self.title_entry = ctk.CTkEntry(form_frame, width=200)
        self.title_entry.grid(row=0, column=1, pady=5)

        # List Name
        ctk.CTkLabel(form_frame, text="List Name:").grid(
            row=1, column=0, sticky="w", pady=5)
        self.list_entry = ctk.CTkEntry(form_frame, width=200)
        self.list_entry.grid(row=1, column=1, pady=5)

        # Due Date
        ctk.CTkLabel(form_frame, text="Due Date (YYYY-MM-DD):").grid(
            row=2, column=0, sticky="w", pady=5)
        self.due_entry = ctk.CTkEntry(form_frame, width=200)
        self.due_entry.grid(row=2, column=1, pady=5)

        # Due Time
        ctk.CTkLabel(form_frame, text="Due Time (HH:MM):").grid(
            row=3, column=0, sticky="w", pady=5)
        self.due_time_entry = ctk.CTkEntry(form_frame, width=200)
        self.due_time_entry.grid(row=3, column=1, pady=5)

        # Notes
        ctk.CTkLabel(form_frame, text="Notes:").grid(
            row=4, column=0, sticky="w", pady=5)
        self.notes_entry = ctk.CTkEntry(form_frame, width=200)
        self.notes_entry.grid(row=4, column=1, pady=5)

        # # Status
        # ctk.CTkLabel(form_frame, text="Status:").grid(
        #     row=4, column=0, sticky="w", pady=5)
        # self.status_var = ctk.StringVar(value="needsAction")
        # self.status_menu = ctk.CTkOptionMenu(
        #     form_frame, variable=self.status_var, values=["needsAction", "completed"])
        # self.status_menu.grid(row=4, column=1, pady=5)

        self.actions_area = ctk.CTkFrame(self.act_win)
        self.actions_area.pack(pady=10)

        if not edit:
            ctk.CTkButton(self.actions_area, text="Add",
                          command=lambda:
                          self.add_task()
                          ).pack(
                side="left", padx=5)
            ctk.CTkButton(self.actions_area, text="Cancel",
                          command=self.act_win.destroy).pack(
                              side="left", padx=5)
        else:
            ctk.CTkButton(self.actions_area, text="Edit",
                          command=lambda
                          title=self.title_entry.get(),
                          list_name=self.list_entry.get(),
                          due_time=self.due_entry.get(),
                          notes=self.notes_entry.get(), :
                          self.edit_task(
                              task_id, title, list_name, due_time, notes)
                          ).pack(
                side="left", padx=5)
            ctk.CTkButton(self.actions_area, text="Cancel",
                          command=self.act_win.destroy).pack(
                              side="left", padx=5)
            if title is not None:
                self.title_entry.insert(0, str(title))
            if list_name is not None:
                self.list_entry.insert(0, str(list_name))
            if due is not None:
                self.due_entry.insert(0, str(due))
                self.due_time_entry.insert(0, str(due))
            if notes is not None:
                self.notes_entry.insert(0, str(notes))

    def edit_task_win(self, task_id):
        task = list(get_task_by_id(task_id))
        tid = task[0]
        title = task[1]
        list_name = task[2]
        due = task[3]
        notes = task[4]

        self.task_maker_win(True, tid, title,
                            list_name,
                            due,
                            notes,
                            "needsAction",
                            )

    def add_task(self, title=None, list_name="", due_time=None, notes=""):
        """function for add Button when making tasks"""
        title = self.title_entry.get()
        list_name = self.list_entry.get()
        due_time = self.due_entry.get()
        notes = self.notes_entry.get()
        add_local_task(title, list_name, due_time, notes)
        self.refresh()
        self.act_win.destroy()

    def order_tasks(self):
        pass

    def delete_task(self, task_id):
        """Delete the task"""
        delete_local_task(task_id)
        self.refresh()  # refresh

    def edit_task(self, task_id, title, list_name, due_time, notes):
        """edit task just like add but modification"""
        self.add_task(title, list_name, due_time, notes)
        self.delete_task(task_id)

    def push_to_google(self):
        if self.creds is not None:
            push_local_tasks_to_google(self.creds)
        else:
            messagebox.showerror("Get your credentials from google cloud",
                                 "You have to connect with your google account first")

        self.refresh()

    def sync_from_google(self):
        tasks = get_tasks_online(self.creds)
        for task in tasks:
            insert_task_to_db(task)
        self.refresh()
        return True

    def update_completed_tasks(self):
        update_google_tasks_from_local(self.creds)
        self.refresh()


class taskApp(app):
    """An online functions"""

    def __init__(self, master) -> None:
        initialize_database()
        self.master = master
        super().__init__(self.master)

        self.master.title("BobsiMo Activities")
        self.master.geometry("700x500")
        self.master.iconbitmap("favicon.png")

        header_frame = ctk.CTkFrame(master, height=30)
        header_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(header_frame,
                      text="Refresh", width=60, fg_color=self.dark_grey,
                      command=self.refresh).pack(side="right")

        ctk.CTkButton(header_frame,
                      text="Sync with Google", width=60, fg_color=self.dark_grey,
                      command=self._sync_engine).pack(side="right", padx=10)

        # Create scrollable frame for tasks
        self.scrollable_frame = ctk.CTkScrollableFrame(
            master, width=480, height=200)
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(master)
        btn_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkButton(btn_frame, text="Add Task",
                      command=self.task_maker_win).pack(side="right")

        self.refresh()

    def sync(self):
        """Establish the 2way street between this and google. If there
        are any here that aren't on google, then push them

        if there are tasks on google that aren't here, bring them here

        This (for now) deals with only adding not deleting.

        if i delete from my google account and the same task is here
        then it has to change because that is what syncing is.

        normally then it must take into account the status closely.

        but a deleted task isn't same as a completed one.
        maybe while syncing, check if the ones going 


        i sense a cycle. where you might have moved and you sync here only
        to see that you have the same task from your computer.

        So maybe instead of really removing them from this local db
        maybe we can mark it as deleted so that we can make an API call
        to delete that exact task. All this while syncing, we are trying to mirror
        """
        if self.sync_from_google():
            self.push_to_google()

    def _sync_engine(self):
        import threading
        t = threading.Thread(target=self.sync)
        t.daemon = True
        t.start()


def main():
    root = ctk.CTk()
    taskApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
