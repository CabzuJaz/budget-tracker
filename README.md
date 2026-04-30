# Budget Tracker (Python CLI)

A simple offline budget tracker with billing cycle awareness.

## Features

* 4 Categories (Cash, Ralph_CC, Jazz_CC, Spaylater)
* Billing cycle calculation
* Current cycle due tracking
* Upcoming bills dashboard
* Paid / Unpaid tagging
* Export to Excel

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Build EXE

```bash
pyinstaller --onefile --noconsole main.py
```

## Notes

* Date format: `Apr 30, 2026`
* Data stored in `.txt` files
* Excel export: `budget_report.xlsx`
