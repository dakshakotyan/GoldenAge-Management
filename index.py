import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import sqlite3
import subprocess
import matplotlib.pyplot as plt

root = tk.Tk()
root.title("GoldenAge Care System")
root.state("zoomed")

staff_logged_in = False

conn = sqlite3.connect("goldenage.db")
cursor = conn.cursor()
last_emergency_id = 0

cursor.execute("""
CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age TEXT,
    gender TEXT,
    reason TEXT,
    bp TEXT,
    sugar TEXT
)
""")
try:
    cursor.execute("ALTER TABLE residents ADD COLUMN reason TEXT")
except:
    pass

cursor.execute("""
CREATE TABLE IF NOT EXISTS emergency_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER,
    name TEXT,
    bp TEXT,
    sugar TEXT,
    status TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    status TEXT DEFAULT 'Unread'
)
""")
conn.commit()

def open_admin():
    try:
        subprocess.Popen(["python", "admin.py"])
    except:
        messagebox.showerror("Error", "admin.py file not found")

original_bg = Image.open(r"C:\python project\oldageback.jpg")

bg_label = tk.Label(root)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

def resize_background(event):
    if event.width < 1 or event.height < 1:
        return
    resized = original_bg.resize((event.width, event.height))
    bg_photo = ImageTk.PhotoImage(resized)
    bg_label.config(image=bg_photo)
    bg_label.image = bg_photo

root.bind("<Configure>", resize_background)

def get_resident_count():
    cursor.execute("SELECT COUNT(*) FROM residents")
    return cursor.fetchone()[0]


def get_emergency_count():
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT resident_id, MAX(id) as latest_id
            FROM emergency_requests
            GROUP BY resident_id
        ) latest
        JOIN emergency_requests e
        ON e.id = latest.latest_id
        WHERE e.status = 'Pending'
    """)

    result = cursor.fetchone()[0]
    return result if result else 0
def get_pending_requests_count():
    cursor.execute("""
        SELECT COUNT(*) FROM emergency_requests WHERE status='Pending'
    """)
    result = cursor.fetchone()[0]
    return result if result else 0

def open_staff():
    login = tk.Toplevel(root)
    login.title("Staff Login")
    login.geometry("300x250")

    tk.Label(login, text="Staff Login", font=("Arial", 16, "bold")).pack(pady=10)

    tk.Label(login, text="Username").pack()
    username = tk.Entry(login)
    username.pack()

    tk.Label(login, text="Password").pack()
    password = tk.Entry(login, show="*")
    password.pack()

    def check_login():
        global staff_logged_in
        if username.get() == "staff" and password.get() == "1234":
            staff_logged_in = True
            messagebox.showinfo("Login Success", "Welcome Staff")
            login.destroy()
        else:
            messagebox.showerror("Error", "Invalid Login")

    tk.Button(login, text="Login", bg="green", fg="white",
              command=check_login).pack(pady=15)

def check_staff():
    if not staff_logged_in:
        messagebox.showerror("Access Denied", "Please login as Staff first")
        return False
    return True

def is_emergency(bp, sugar):
    try:
        if "/" not in bp:
            return None

        sys, dia = bp.split("/")
        sys = int(sys.strip())
        dia = int(dia.strip())
        sugar = int(sugar)

        if sys >= 140 or dia >= 90:
            return True

        if sys <= 80 or dia <= 50:
            return True

        if sugar >= 200 or sugar <= 60:
            return True

        return False

    except:
        return None

def add_resident():
    if not check_staff():
        return

    win = tk.Toplevel(root)
    win.title("Add Resident")
    win.geometry("400x500")

    tk.Label(win, text="Add Resident", font=("Arial", 16, "bold")).pack(pady=10)

    tk.Label(win, text="Name").pack()
    name = tk.Entry(win)
    name.pack()

    tk.Label(win, text="Age").pack()
    age = tk.Entry(win)
    age.pack()

    tk.Label(win, text="Gender").pack()
    gender = ttk.Combobox(win, values=["Male", "Female", "Other"])
    gender.pack()

    tk.Label(win, text="Reason for Admission").pack()
    reason = tk.Entry(win)
    reason.pack()

    def save():
        try:
            age_val = int(age.get())

            if age_val < 60:
                messagebox.showerror("Error", "Only residents age above 60 allowed")
                return

            if reason.get() == "":
                messagebox.showerror("Error", "Please enter reason for admission")
                return

            cursor.execute(
                "INSERT INTO residents (name, age, gender, reason, bp, sugar) VALUES (?, ?, ?, ?, ?, ?)",
                (name.get(), age_val, gender.get(), reason.get(), "", "")
            )
            conn.commit()
            # Notify Admin
            msg = f"New resident added: {name.get()}. Please review the admission reason."

            cursor.execute("""
                INSERT INTO notifications (message, status)
                VALUES (?, 'Unread')
            """, (msg,))

            conn.commit()

            messagebox.showinfo("Success", "Resident Added Successfully")
            win.destroy()

        except:
            messagebox.showerror("Error", "Enter valid details")

    tk.Button(win, text="Save", bg="green", fg="white", command=save).pack(pady=10)

def update_health():
    if not check_staff():
        return

    win = tk.Toplevel(root)
    win.title("Update Health")
    win.geometry("400x400")

    tk.Label(win, text="Update Health", font=("Arial", 16, "bold")).pack(pady=10)

    cursor.execute("SELECT id, name FROM residents")
    residents = cursor.fetchall()
    options = [f"{r[0]} - {r[1]}" for r in residents]

    tk.Label(win, text="Select Resident").pack()
    selected = ttk.Combobox(win, values=options)
    selected.pack()

    tk.Label(win, text="BP (e.g. 120/80)").pack()
    bp = tk.Entry(win)
    bp.pack()

    tk.Label(win, text="Sugar").pack()
    sugar = tk.Entry(win)
    sugar.pack()

    def save_health():
        if selected.get() == "":
            messagebox.showerror("Error", "Select Resident")
            return

        if bp.get() == "" or sugar.get() == "":
            messagebox.showerror("Error", "Enter BP and Sugar")
            return

        result = is_emergency(bp.get(), sugar.get())

        if result is None:
            messagebox.showerror("Error", "Invalid BP format (use 120/80)")
            return

        res_id = selected.get().split(" - ")[0]
        res_name = selected.get().split(" - ")[1]

        cursor.execute(
            "UPDATE residents SET bp=?, sugar=? WHERE id=?",
            (bp.get(), sugar.get(), res_id)
        )
        conn.commit()

        if result:
            cursor.execute("""
                INSERT INTO emergency_requests
                (resident_id, name, bp, sugar, status)
                VALUES (?, ?, ?, ?, ?)
            """, (res_id, res_name, bp.get(), sugar.get(), "Pending"))

            conn.commit()

            messagebox.showwarning(
                "🚨 Emergency Alert",
                f"{res_name} has abnormal BP/Sugar!"
            )

        else:
            # Remove old emergency requests if health becomes normal
            cursor.execute("""
                DELETE FROM emergency_requests
                WHERE resident_id=?
            """, (res_id,))

            conn.commit()

            messagebox.showinfo(
                "Success",
                "Health Updated - Normal\nEmergency request removed."
            )

        win.destroy()

    tk.Button(win, text="Save", bg="green", fg="white",
              command=save_health).pack(pady=15)

def view_emergency():
    win = tk.Toplevel(root)
    win.title("Emergency Requests")
    win.geometry("650x400")

    tree2 = ttk.Treeview(win, columns=("ID", "Name", "BP", "Sugar", "Status"), show="headings")

    for col in ("ID", "Name", "BP", "Sugar", "Status"):
        tree2.heading(col, text=col)

    tree2.pack(fill="both", expand=True)

    # ALWAYS FRESH QUERY
    cursor.execute("SELECT id, name, bp, sugar, status FROM emergency_requests")
    rows = cursor.fetchall()

    tree2.delete(*tree2.get_children())

    for row in rows:
        tree2.insert("", "end", values=row)

def view_records():
    win = tk.Toplevel(root)
    win.title("Residents List")
    win.geometry("800x400")

    tree = ttk.Treeview(
        win,
        columns=("ID", "Name", "Age", "Gender", "Reason", "BP", "Sugar"),
        show="headings"
    )

    tree.heading("ID", text="ID")
    tree.heading("Name", text="Name")
    tree.heading("Age", text="Age")
    tree.heading("Gender", text="Gender")
    tree.heading("Reason", text="Reason")
    tree.heading("BP", text="BP")
    tree.heading("Sugar", text="Sugar")

    tree.pack(fill="both", expand=True)

    cursor.execute("SELECT id, name, age, gender, reason, bp, sugar FROM residents")

    for row in cursor.fetchall():
        tree.insert("", "end", values=row)
def view_reports():

    win = tk.Toplevel(root)
    win.title("Health Reports & Graphs")
    win.geometry("650x550")

    cursor.execute("""
        SELECT id, name, bp, sugar
        FROM residents
    """)

    data = cursor.fetchall()

    normal = 0
    emergency = 0

    for resident_id, name, bp, sugar in data:

        if bp == "" or sugar == "":
            normal += 1
            continue

        try:
            result = is_emergency(bp, sugar)

            if result is True:
                emergency += 1

            else:
                normal += 1

        except:
            normal += 1

    total = normal + emergency

    tk.Label(
        win,
        text="Health Report Dashboard",
        font=("Arial", 18, "bold")
    ).pack(pady=10)

    tk.Label(
        win,
        text=f"Total Current Residents: {total}",
        font=("Arial", 12, "bold")
    ).pack(pady=5)

    tk.Label(
        win,
        text=f"Normal Residents: {normal}",
        fg="green",
        font=("Arial", 12, "bold")
    ).pack(pady=5)

    tk.Label(
        win,
        text=f"Emergency Residents: {emergency}",
        fg="red",
        font=("Arial", 12, "bold")
    ).pack(pady=5)

    plt.figure(figsize=(5, 5))

    plt.pie(
        [normal, emergency],
        labels=["Normal", "Emergency"],
        autopct="%1.1f%%",
        colors=["green", "red"],
        startangle=90
    )

    plt.title("Resident Health Status")
    plt.show()
def view_notifications():
    win = tk.Toplevel(root)
    win.title("Notifications")
    win.geometry("600x400")

    tree = ttk.Treeview(
        win,
        columns=("ID", "Message", "Status"),
        show="headings"
    )

    for col in ("ID", "Message", "Status"):
        tree.heading(col, text=col)

    tree.pack(fill="both", expand=True)

    cursor.execute("""
        UPDATE notifications
        SET status='Read'
        WHERE status='Unread'
    """)
    conn.commit()

    cursor.execute("""
        SELECT id, message, status
        FROM notifications
    """)

    for row in cursor.fetchall():
        tree.insert("", "end", values=row)

    def delete_notification():
        selected = tree.focus()

        if not selected:
            messagebox.showerror("Error", "Select notification")
            return

        data = tree.item(selected)["values"]

        cursor.execute(
            "DELETE FROM notifications WHERE id=?",
            (data[0],)
        )
        conn.commit()

        tree.delete(selected)

        messagebox.showinfo(
            "Deleted",
            "Notification deleted successfully"
        )

    tk.Button(
        win,
        text="Delete Notification",
        bg="red",
        fg="white",
        command=delete_notification
    ).pack(pady=10)

header = tk.Frame(root, bg="#0f172a", height=70)
header.pack(fill="x")

title = tk.Label(header, text="GoldenAge Care System",
                 font=("Arial", 22, "bold"),
                 fg="white", bg="#0f172a")
title.pack(side="left", padx=25, pady=15)

nav_frame = tk.Frame(header, bg="#0f172a")
nav_frame.pack(side="right", padx=20)

for item in ["Home", "Admin", "Staff", "Reports"]:

    if item == "Staff":
        cmd = open_staff
    elif item == "Admin":
        cmd = open_admin
    elif item=="Reports":
        cmd = view_reports
    else:
        cmd=None


    tk.Button(nav_frame, text=item, bg="#0f172a", fg="white",
              bd=0, command=cmd).pack(side="left", padx=12)

main_container = tk.Frame(root, bg="#ffffff")
main_container.place(relx=0.5, rely=0.52, anchor="center", width=1150, height=600)

sidebar = tk.Frame(main_container, bg="#1e293b", width=220)
sidebar.pack(side="left", fill="y")

tk.Label(sidebar, text="Dashboard", font=("Arial", 18, "bold"),
         fg="white", bg="#1e293b").pack(pady=25)

menu_items = [
    ("Resident Details", view_records),
    ("Health Records", update_health),
    ("Emergency Requests", view_emergency),
    ("Admissions", add_resident),
    ("Notifications", view_notifications),
    ("Reports & Graphs", view_reports)

]

for text, cmd in menu_items:
    tk.Button(sidebar, text=text, width=18, bg="#334155",
              fg="white", bd=0, command=cmd).pack(pady=8)

content = tk.Frame(main_container, bg="white")
content.pack(side="right", expand=True, fill="both")

tk.Label(content, text="Welcome to GoldenAge Care System",
         font=("Arial", 24, "bold"), bg="white").pack(pady=20)

cards_frame = tk.Frame(content, bg="white")
cards_frame.pack(pady=35)

def create_stat_card(parent, title, value, color):
    card = tk.Frame(parent, bg=color, width=180, height=110)
    card.pack(side="left", padx=20)
    card.pack_propagate(False)

    value_label = tk.Label(card, text=value, font=("Arial", 24, "bold"),
                           fg="white", bg=color)
    value_label.pack(pady=12)

    tk.Label(card, text=title, font=("Arial", 11),
             fg="white", bg=color).pack()

    return value_label, card

res_label, _ = create_stat_card(cards_frame, "Residents", "0", "#2563eb")
create_stat_card(cards_frame, "Staff", "25", "#16a34a")
emg_label, emg_card = create_stat_card(cards_frame, "Emergencies", "0", "#dc2626")
pending_label, _ = create_stat_card(cards_frame, "Pending Requests", "0", "#9333ea")

def update_cards():
    res_label.config(text=str(get_resident_count()))
    emg_count = get_emergency_count()
    emg_label.config(text=str(emg_count))
    pending_label.config(text=str(get_pending_requests_count()))

    if emg_count > 0:
        current = emg_card.cget("bg")
        new = "#7f1d1d" if current == "#dc2626" else "#dc2626"
        emg_card.config(bg=new)
        for w in emg_card.winfo_children():
            w.config(bg=new)
    else:
        emg_card.config(bg="#dc2626")
        for w in emg_card.winfo_children():
            w.config(bg="#dc2626")

    root.after(1000, update_cards)

update_cards()
def check_new_emergency():
    global last_emergency_id

    cursor.execute("""
        SELECT id, name, bp, sugar 
        FROM emergency_requests 
        ORDER BY id DESC LIMIT 1
    """)

    row = cursor.fetchone()

    if row:
        current_id, name, bp, sugar = row

        if current_id > last_emergency_id:
            last_emergency_id = current_id

            # 🔔 POPUP ALERT
            messagebox.showwarning(
                "🚨 New Emergency Alert",
                f"{name} has abnormal health!\nBP: {bp} | Sugar: {sugar}"
            )

    # ⏱ check every 2 seconds
    root.after(2000, check_new_emergency)

action_frame = tk.Frame(content, bg="white")
action_frame.pack(pady=25)

actions = [
    ("Add Resident", add_resident),
    ("Update Health", update_health),
    ("View Reports", view_records)
]

for text, cmd in actions:
    tk.Button(action_frame, text=text, bg="#0ea5e9",
              fg="white", command=cmd).pack(side="left", padx=15)

# ================= FOOTER =================
footer = tk.Frame(root, bg="#0f172a", height=35)
footer.pack(side="bottom", fill="x")

tk.Label(footer,
         text="© 2026 GoldenAge Care System | Python Tkinter + SQLite + Matplotlib",
         fg="white", bg="#0f172a").pack(pady=8)
check_new_emergency()

root.mainloop()