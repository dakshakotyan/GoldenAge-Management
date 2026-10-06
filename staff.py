import tkinter as tk
from tkinter import messagebox
import sqlite3

root = tk.Tk()
root.title("Staff Panel")
root.geometry("400x450")

conn = sqlite3.connect("goldenage.db")
cursor = conn.cursor()

tk.Label(root, text="Staff - Add Resident",
         font=("Arial", 16, "bold")).pack(pady=10)

tk.Label(root, text="Name").pack()
name = tk.Entry(root)
name.pack()

tk.Label(root, text="Age").pack()
age = tk.Entry(root)
age.pack()

tk.Label(root, text="Gender").pack()
gender = tk.Entry(root)
gender.pack()

tk.Label(root, text="BP").pack()
bp = tk.Entry(root)
bp.pack()

tk.Label(root, text="Sugar").pack()
sugar = tk.Entry(root)
sugar.pack()

def save():
    cursor.execute(
        "INSERT INTO residents (name, age, gender, bp, sugar) VALUES (?, ?, ?, ?, ?)",
        (name.get(), age.get(), gender.get(), bp.get(), sugar.get())
    )
    conn.commit()
    messagebox.showinfo("Success", "Resident Added")

    name.delete(0, tk.END)
    age.delete(0, tk.END)
    gender.delete(0, tk.END)
    bp.delete(0, tk.END)
    sugar.delete(0, tk.END)

tk.Button(root, text="Add Resident",
          bg="blue", fg="white",
          command=save).pack(pady=20)

root.mainloop()