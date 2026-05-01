import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FILE = "Expenses.txt"

OUTPUT_FILES = {
    "Cash": "Cash.txt",
    "Ralph_CC": "Ralph_CC.txt",
    "Jazz_CC": "Jazz.txt",
    "Spaylater": "Spaylater.txt"
}

CASH_ON_HAND_FILE = "Cash_on_Hand.txt"

# ======================
# UTIL
# ======================

def parse_date(s):
    return datetime.strptime(s, "%m%d%y")

def format_date(d):
    return d.strftime("%m%d%y")

def ensure_file(name):
    path = os.path.join(BASE_DIR, name)
    if not os.path.exists(path):
        open(path, "w").close()
    return path

def prev_month(y, m):
    return (y-1, 12) if m == 1 else (y, m-1)

def next_month(y, m):
    return (y+1, 1) if m == 12 else (y, m+1)

# ======================
# LOGIC
# ======================

def get_cycle_range(category, date):
    y, m, d = date.year, date.month, date.day

    if category in ["Ralph_CC", "Spaylater"]:
        if d <= 25:
            py, pm = prev_month(y, m)
            return datetime(py, pm, 26), datetime(y, m, 25)
        else:
            ny, nm = next_month(y, m)
            return datetime(y, m, 26), datetime(ny, nm, 25)

    if category == "Jazz_CC":
        if d <= 15:
            py, pm = prev_month(y, m)
            return datetime(py, pm, 16), datetime(y, m, 15)
        else:
            ny, nm = next_month(y, m)
            return datetime(y, m, 16), datetime(ny, nm, 15)

def get_due_date(category, cycle_end):
    if category == "Ralph_CC":
        return cycle_end + timedelta(days=20)

    if category in ["Jazz_CC", "Spaylater"]:
        return datetime(
            cycle_end.year + (cycle_end.month // 12),
            (cycle_end.month % 12) + 1,
            5
        )
        

# ======================
# DATA
# ======================

def load_all():
    path = ensure_file(MASTER_FILE)
    data = []

    with open(path) as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 6:
                continue
            data.append({
                "date": parse_date(parts[0]),
                "category": parts[1],
                "desc": parts[2],
                "amount": float(parts[3]),
                "due": parts[4],
                "status": parts[5]
            })
    return data

def save_all(data):
    with open(MASTER_FILE, "w") as f:
        for r in data:
            f.write(f"{format_date(r['date'])}|{r['category']}|{r['desc']}|{r['amount']}|{r['due']}|{r['status']}\n")

# ======================
# FILE GENERATION
# ======================

def regenerate_files(data):
    for f in OUTPUT_FILES.values():
        open(f, "w").close()
    open(CASH_ON_HAND_FILE, "w").close()

    balance = 0

    for r in sorted(data, key=lambda x: x["date"]):
        cat = r["category"]

        if cat in OUTPUT_FILES:
            with open(OUTPUT_FILES[cat], "a") as f:
                f.write(f"{format_date(r['date'])}|{r['desc']}|{r['amount']}|{r['due']}|{r['status']}\n")

        if cat == "Cash":
            balance += r["amount"]
            with open(CASH_ON_HAND_FILE, "a") as f:
                f.write(f"{format_date(r['date'])}|{r['desc']}|{r['amount']}|BAL:{balance}\n")

# ======================
# GUI
# ======================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Budget Tracker")

        # Inputs
        tk.Label(root, text="Date (MMDDYY)").grid(row=0, column=0)
        tk.Label(root, text="Category").grid(row=1, column=0)
        tk.Label(root, text="Description").grid(row=2, column=0)
        tk.Label(root, text="Amount").grid(row=3, column=0)

        self.date = tk.Entry(root)
        self.date.grid(row=0, column=1)

        self.category = ttk.Combobox(root, values=["Cash", "Ralph_CC", "Jazz_CC", "Spaylater"])
        self.category.grid(row=1, column=1)

        self.desc = tk.Entry(root)
        self.desc.grid(row=2, column=1)

        self.amount = tk.Entry(root)
        self.amount.grid(row=3, column=1)

        tk.Button(root, text="Add Expense", command=self.add).grid(row=4, column=0, columnspan=2)

        tk.Button(root, text="Mark Paid", command=self.mark_paid).grid(row=5, column=0, columnspan=2)

        tk.Button(root, text="Dashboard", command=self.dashboard).grid(row=6, column=0, columnspan=2)

        tk.Button(root, text="Clear All", command=self.clear).grid(row=7, column=0, columnspan=2)

        # Table
        self.tree = ttk.Treeview(root, columns=("date","cat","desc","amt","due","status"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)

        self.tree.grid(row=0, column=2, rowspan=8)

        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        for r in load_all():
            self.tree.insert("", "end", values=(
                format_date(r["date"]),
                r["category"],
                r["desc"],
                r["amount"],
                r["due"],
                r["status"]
            ))

    def add(self):
        try:
            d = parse_date(self.date.get())
            cat = self.category.get()
            desc = self.desc.get()
            amt = float(self.amount.get())

            data = load_all()

            if cat == "Cash":
                data.append({"date": d, "category": cat, "desc": desc, "amount": -amt, "due": "", "status": ""})
            else:
                _, end = get_cycle_range(cat, d)
                due = get_due_date(cat, end)
                data.append({"date": d, "category": cat, "desc": desc, "amount": amt, "due": format_date(due), "status": "UNPAID"})

            save_all(data)
            regenerate_files(data)
            self.refresh()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def mark_paid(self):
        selected = self.tree.selection()
        if not selected:
            return

        index = self.tree.index(selected[0])
        data = load_all()

        data[index]["status"] = "PAID"

        save_all(data)
        regenerate_files(data)
        self.refresh()

    def dashboard(self):
        data = load_all()
        today = datetime.today()

        msg = ""
        overall_total = 0

        results = []

        for cat in ["Ralph_CC", "Jazz_CC", "Spaylater"]:
            start, end = get_cycle_range(cat, today)
            due = get_due_date(cat, end)

            total = sum(
                r["amount"]
                for r in data
                if r["category"] == cat
                and start <= r["date"] <= end
                and r["status"] == "UNPAID"
            )

            overall_total += total

            days = (due - today).days
            results.append((cat, total, due, days))

        # sort by nearest due
        results.sort(key=lambda x: x[2])

        for r in results:
            msg += f"{r[0]}\n"
            msg += f"Due: {format_date(r[2])} | Amount: {r[1]} | Days: {r[3]}\n\n"

        msg += "----------------------\n"
        msg += f"OVERALL DUE: {overall_total}\n"

        # highlight most urgent
        if results:
            msg += f"\n MOST URGENT: {results[0][0]}"

        messagebox.showinfo("Dashboard", msg)

    def clear(self):
        if messagebox.askyesno("Confirm", "Clear all data?"):
            open(MASTER_FILE, "w").close()
            regenerate_files([])
            self.refresh()

# ======================
# RUN
# ======================

root = tk.Tk()
app = App(root)
root.mainloop()