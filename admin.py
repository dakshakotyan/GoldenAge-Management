import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3

conn = sqlite3.connect("goldenage.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE residents
        ADD COLUMN notification_seen TEXT DEFAULT 'No'
    """)
    conn.commit()
except:
    pass

# ================= ADD NEW COLUMN (SAFE) =================
try:
    cursor.execute("ALTER TABLE residents ADD COLUMN reason_status TEXT DEFAULT 'Pending'")
except:
    pass

def admin_login():
    login = tk.Tk()
    login.title("Admin Login")
    login.geometry("300x220")

    tk.Label(login, text="Admin Login", font=("Arial", 16, "bold")).pack(pady=10)

    tk.Label(login, text="Username").pack()
    user = tk.Entry(login)
    user.pack()

    tk.Label(login, text="Password").pack()
    pwd = tk.Entry(login, show="*")
    pwd.pack()

    def check():
        if user.get() == "admin" and pwd.get() == "admin123":
            login.destroy()
            open_admin_panel()
        else:
            messagebox.showerror("Error", "Invalid Admin Login")

    tk.Button(login, text="Login", bg="green", fg="white", command=check).pack(pady=15)

    login.mainloop()


# ================= ADMIN PANEL =================
def open_admin_panel():
    root = tk.Tk()
    root.title("Admin Panel")
    root.geometry("1000x600")

    tk.Label(root, text="Admin Dashboard", font=("Arial", 18, "bold")).pack(pady=10)

    # ================= RESIDENT TABLE =================
    tree = ttk.Treeview(
        root,
        columns=("ID", "Name", "Age", "Gender", "Reason", "Status", "BP", "Sugar"),
        show="headings"
    )

    for col in ("ID", "Name", "Age", "Gender", "Reason", "Status", "BP", "Sugar"):
        tree.heading(col, text=col)

    tree.pack(fill="both", expand=True)

    # ================= LOAD DATA =================
    def load_data():
        tree.delete(*tree.get_children())

        cursor.execute("""
            SELECT id, name, age, gender, reason, reason_status, bp, sugar 
            FROM residents
        """)

        for row in cursor.fetchall():
            tree.insert("", "end", values=row)

    load_data()
    # ================= PENDING REASON ALERT =================
    cursor.execute("""
        SELECT name, reason
        FROM residents
        WHERE reason_status='Pending'
    """)

    pending = cursor.fetchall()

    if pending:
        msg = ""

        for name, reason in pending:
            msg += f"{name}\nReason: {reason}\n\n"

        messagebox.showinfo(
            "New Resident Admission Requests",
            f"Please review the following residents:\n\n{msg}"
        )
        cursor.execute("""
        UPDATE residents
        SET notification_seen='Yes'
        WHERE notification_seen='No'
        """)
        conn.commit()

    # ================= EDIT RESIDENT =================
    def edit_resident():
        selected = tree.focus()
        if not selected:
            messagebox.showerror("Error", "Select resident")
            return

        data = tree.item(selected)["values"]

        win = tk.Toplevel(root)
        win.title("Edit Resident")

        tk.Label(win, text="Name").pack()
        name = tk.Entry(win)
        name.insert(0, data[1])
        name.pack()

        tk.Label(win, text="Age").pack()
        age = tk.Entry(win)
        age.insert(0, data[2])
        age.pack()

        tk.Label(win, text="Gender").pack()
        gender = tk.Entry(win)
        gender.insert(0, data[3])
        gender.pack()



        def save():
            cursor.execute("""
                UPDATE residents 
                SET name=?, age=?, gender=?
                WHERE id=?
            """, (name.get(), age.get(), gender.get(),data[0]))

            conn.commit()
            messagebox.showinfo("Updated", "Resident Updated")
            win.destroy()
            load_data()

        tk.Button(win, text="Save", bg="green", fg="white", command=save).pack(pady=10)

    # ================= DELETE RESIDENT =================
    def delete_resident():
        selected = tree.focus()
        if not selected:
            messagebox.showerror("Error", "Select resident")
            return

        data = tree.item(selected)["values"]

        confirm = messagebox.askyesno("Confirm", "Delete this resident?")
        if confirm:
            cursor.execute("DELETE FROM residents WHERE id=?", (data[0],))
            cursor.execute("DELETE FROM emergency_requests WHERE resident_id=?", (data[0],))
            conn.commit()
            load_data()
            messagebox.showinfo("Deleted", "Resident removed")

    # ================= UPDATE HEALTH =================
    def update_health():
        selected = tree.focus()
        if not selected:
            messagebox.showerror("Error", "Select resident")
            return

        data = tree.item(selected)["values"]

        win = tk.Toplevel(root)
        win.title("Update Health")

        tk.Label(win, text="BP (120/80)").pack()
        bp = tk.Entry(win)
        bp.pack()

        tk.Label(win, text="Sugar").pack()
        sugar = tk.Entry(win)
        sugar.pack()

        def check_emergency(bp, sugar):
            try:
                sys, dia = map(int, bp.split("/"))
                sugar = int(sugar)

                if sys > 130 or dia > 80 or sys < 90 or dia < 60:
                    return True
                if sugar < 70 or sugar > 140:
                    return True
                return False
            except:
                return False

        def save():
            cursor.execute("""
                UPDATE residents SET bp=?, sugar=? WHERE id=?
            """, (bp.get(), sugar.get(), data[0]))

            conn.commit()

            if check_emergency(bp.get(), sugar.get()):
                cursor.execute("""
                    INSERT INTO emergency_requests (resident_id, name, bp, sugar, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (data[0], data[1], bp.get(), sugar.get(), "Pending"))

                conn.commit()
                messagebox.showwarning("🚨 Emergency", "Consult doctor immediately!")
            else:
                messagebox.showinfo("Success", "Health Updated")

            win.destroy()
            load_data()

        tk.Button(win, text="Save", bg="green", fg="white", command=save).pack(pady=10)

    # ================= REASON APPROVAL SYSTEM =================
    def review_reason(status_value):

        selected = tree.focus()

        if not selected:
            messagebox.showerror("Error", "Select resident")
            return

        data = tree.item(selected)["values"]

        resident_id = data[0]
        resident_name = data[1]

        # ================= ACCEPT =================
        if status_value == "Accepted":

            cursor.execute("""
                UPDATE residents
                SET reason_status=?
                WHERE id=?
            """, (status_value, resident_id))

            msg = f"Admin accepted reason of {resident_name}"

            cursor.execute("""
                INSERT INTO notifications (message, status)
                VALUES (?, 'Unread')
            """, (msg,))

            conn.commit()

            messagebox.showinfo("Accepted", "Reason Approved Successfully")

        # ================= REJECT =================
        elif status_value == "Rejected":

            # Notification
            msg = f"Admin rejected reason of {resident_name}"

            cursor.execute("""
                INSERT INTO notifications (message, status)
                VALUES (?, 'Unread')
            """, (msg,))

            # DELETE from residents
            cursor.execute("""
                DELETE FROM residents
                WHERE id=?
            """, (resident_id,))

            # DELETE from emergency table
            cursor.execute("""
                DELETE FROM emergency_requests
                WHERE resident_id=?
            """, (resident_id,))

            conn.commit()

            messagebox.showinfo(
                "Rejected",
                "Reason rejected and resident removed completely"
            )

        load_data()

    # ================= EMERGENCY VIEW =================
    def view_emergency():
        win = tk.Toplevel(root)
        win.title("Emergency Requests")
        win.geometry("650x400")

        tree2 = ttk.Treeview(
            win,
            columns=("ID", "Name", "BP", "Sugar", "Status"),
            show="headings"
        )

        for col in ("ID", "Name", "BP", "Sugar", "Status"):
            tree2.heading(col, text=col)

        tree2.pack(fill="both", expand=True)

        cursor.execute("""
            SELECT id, name, bp, sugar, status 
            FROM emergency_requests
        """)

        for row in cursor.fetchall():
            tree2.insert("", "end", values=row)

        def update_status(new_status):

            selected = tree2.focus()

            if not selected:
                return

            data = tree2.item(selected)["values"]

            emergency_id = data[0]
            resident_name = data[1]

            # ================= CONSULTED =================
            if new_status == "Consulted":

                # Update resident health to normal
                cursor.execute("""
                    UPDATE residents
                    SET bp='120/80',
                        sugar='100'
                    WHERE name=?
                """, (resident_name,))

                # DELETE emergency request completely
                cursor.execute("""
                    DELETE FROM emergency_requests
                    WHERE id=?
                """, (emergency_id,))

            else:
                # For Approved
                cursor.execute("""
                    UPDATE emergency_requests
                    SET status=?
                    WHERE id=?
                """, (new_status, emergency_id))

            conn.commit()

            messagebox.showinfo(
                "Updated",
                f"Marked as {new_status}"
            )

            win.destroy()

        tk.Button(win, text="Approved", bg="green", fg="white",
                  command=lambda: update_status("Approved")).pack(side="left", padx=10)

        tk.Button(win, text="Consulted", bg="orange", fg="white",
                  command=lambda: update_status("Consulted")).pack(side="left", padx=10)

    # ================= BUTTONS =================
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Edit", bg="blue", fg="white", command=edit_resident).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Delete", bg="red", fg="white", command=delete_resident).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Update Health", bg="purple", fg="white", command=update_health).pack(side="left", padx=10)

    tk.Button(btn_frame, text="Approve Reason", bg="green", fg="white",
              command=lambda: review_reason("Accepted")).pack(side="left", padx=10)

    tk.Button(btn_frame, text="Reject Reason", bg="red", fg="white",
              command=lambda: review_reason("Rejected")).pack(side="left", padx=10)

    tk.Button(btn_frame, text="Emergency Requests", bg="black", fg="white",
              command=view_emergency).pack(side="left", padx=10)

    root.mainloop()


# ================= RUN =================
admin_login()