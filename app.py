from flask import Flask, jsonify, request, send_from_directory
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FILE = os.path.join(BASE_DIR, "Expenses.txt")
OUTPUT_FILES = {
    "Cash": os.path.join(BASE_DIR, "Cash.txt"),
    "Ralph_CC": os.path.join(BASE_DIR, "Ralph_CC.txt"),
    "Jazz_CC": os.path.join(BASE_DIR, "Jazz.txt"),
    "Spaylater": os.path.join(BASE_DIR, "Spaylater.txt")
}
CASH_ON_HAND_FILE = os.path.join(BASE_DIR, "Cash_on_Hand.txt")

app = Flask(__name__, static_folder=BASE_DIR)

# ======================
# UTIL (unchanged)
# ======================

def parse_date(s):
    return datetime.strptime(s, "%m%d%y")

def format_date(d):
    return d.strftime("%m%d%y")

def ensure_file(name):
    if not os.path.exists(name):
        open(name, "w").close()
    return name

def prev_month(y, m):
    return (y-1, 12) if m == 1 else (y, m-1)

def next_month(y, m):
    return (y+1, 1) if m == 12 else (y, m+1)

# ======================
# LOGIC (unchanged)
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
# DATA (unchanged)
# ======================

def load_all():
    ensure_file(MASTER_FILE)
    data = []
    with open(MASTER_FILE) as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 6:
                continue
            data.append({
                "date": format_date(parse_date(parts[0])),
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
            f.write(f"{r['date']}|{r['category']}|{r['desc']}|{r['amount']}|{r['due']}|{r['status']}\n")

def regenerate_files(data):
    for f in OUTPUT_FILES.values():
        open(f, "w").close()
    open(CASH_ON_HAND_FILE, "w").close()
    balance = 0
    for r in sorted(data, key=lambda x: x["date"]):
        cat = r["category"]
        if cat in OUTPUT_FILES:
            with open(OUTPUT_FILES[cat], "a") as f:
                f.write(f"{r['date']}|{r['desc']}|{r['amount']}|{r['due']}|{r['status']}\n")
        if cat == "Cash":
            balance += r["amount"]
            with open(CASH_ON_HAND_FILE, "a") as f:
                f.write(f"{r['date']}|{r['desc']}|{r['amount']}|BAL:{balance}\n")

# ======================
# API ROUTES
# ======================

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "budget_tracker.html")

@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    return jsonify(load_all())

@app.route("/api/expenses", methods=["POST"])
def add_expense():
    body = request.json
    date_str = body["date"]
    cat = body["category"]
    desc = body["desc"]
    amt = float(body["amount"])

    d = parse_date(date_str)
    data = load_all()

    if cat == "Cash":
        entry = {"date": format_date(d), "category": cat,
                 "desc": desc, "amount": -amt, "due": "", "status": ""}
    else:
        _, end = get_cycle_range(cat, d)
        due = get_due_date(cat, end)
        entry = {"date": format_date(d), "category": cat,
                 "desc": desc, "amount": amt,
                 "due": format_date(due), "status": "UNPAID"}

    data.append(entry)
    save_all(data)
    regenerate_files(data)
    return jsonify({"ok": True})

@app.route("/api/expenses/<int:index>/pay", methods=["POST"])
def mark_paid(index):
    data = load_all()
    if index < 0 or index >= len(data):
        return jsonify({"error": "Invalid index"}), 400
    data[index]["status"] = "PAID"
    save_all(data)
    regenerate_files(data)
    return jsonify({"ok": True})

@app.route("/api/expenses/clear", methods=["POST"])
def clear_all():
    open(MASTER_FILE, "w").close()
    regenerate_files([])
    return jsonify({"ok": True})

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    data = load_all()
    today = datetime.today()
    results = []
    overall = 0

    for cat in ["Ralph_CC", "Jazz_CC", "Spaylater"]:
        start, end = get_cycle_range(cat, today)
        due = get_due_date(cat, end)
        total = sum(
            r["amount"] for r in data
            if r["category"] == cat
            and start <= parse_date(r["date"]) <= end
            and r["status"] == "UNPAID"
        )
        overall += total
        days = (due - today).days
        results.append({
            "category": cat,
            "total": total,
            "due": format_date(due),
            "days": days
        })

    results.sort(key=lambda x: x["days"])
    return jsonify({"results": results, "overall": overall})

# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(debug=True, port=5000)