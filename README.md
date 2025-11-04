# taskscheduler

Windows Task Scheduler helper for scheduling Python scripts using PowerShell.

- OS: Windows only (uses `powershell` and `Register-ScheduledTask`).
- Python: 3.9+

## Install (local)

- Editable install for development:

```
pip install -e .
```

This exposes a CLI named `taskscheduler`.

## Quick start

Python API:

```python
from taskscheduler import PythonTask
import sys

# Schedule a daily run at 12:00
PythonTask(
    name="my-task",
    script=r"C:\\path\\to\\job.py",
    python=sys.executable,  # or an explicit path to python.exe
    frequency="Daily",
    at="12:00",
    description="My scheduled job",
).create()
```

CLI:

```
# Create a task that runs daily at 12:00
taskscheduler add --name my-task --script C:\\path\\to\\job.py --python C:\\Path\\To\\Python\\python.exe --frequency Daily --at 12:00

# Create a task that runs once on a specific date/time
taskscheduler add --name one-shot --script C:\\job.py --python C:\\Path\\To\\Python\\python.exe --frequency Once --on 2025-11-10 --at 09:30

# Weekly on Monday and Friday at 07:00
taskscheduler add --name weekly-job --script C:\\job.py --python C:\\Path\\To\\Python\\python.exe --frequency Weekly --on Monday Friday --at 07:00

# Delete, run, check
taskscheduler delete --name my-task
taskscheduler run --name my-task
taskscheduler exists --name my-task
```

## Notes

- If you provide `--user` and `--password`, the task registers to run under those credentials.
- Without credentials, Windows may run the task only when the user is logged in.
- For Weekly frequency, days must be PowerShell-friendly (e.g., Monday, Tuesday, ...).
- This project uses the `src/` layout and a setuptools `pyproject.toml`.

## Limitations

- Windows-only. PowerShell is required and must be on PATH.
- Advanced scheduler features (repetition intervals, conditions, triggers chaining) are not covered.

## User Interface

The package ships with an optional Streamlit UI for browsing and managing tasks.

- Install UI extras:

```
pip install -e .[ui]
# or, after publishing: pip install "taskscheduler[ui]"
```

- Launch the UI (recommended):

```
taskscheduler-ui
```

- Programmatic launch (alternative):

```python
from taskscheduler.ui_launcher import main as launch_ui
launch_ui()
```

### UI Features

- Table of tasks with key fields: Name, Status, Triggers, NextRunTime, LastRunTime, LastRunResult, Author
- Filter: "Only Python tasks" (shows tasks whose action runs Python or a .py script)
- Single-row selection inside the table (click to select)
- Header actions for the selected task:
  - Run ▶️, Enable ✅, Disable 🚫, End ⏹️, Delete 🗑️
- Add ➕ opens a modal to create a new task using PythonTask parameters:
  - Required: Name, Python executable, Python script
  - Optional: Args, Frequency (Once/Daily/Weekly), At (picker or manual HH:MM[:SS]), On (date or days), Description, User, Password, Overwrite

Notes:
- UI requires Streamlit; use the `[ui]` extra.
- Some operations may require appropriate permissions in Windows Task Scheduler.

## Install From GitHub

If you haven't published to PyPI yet, you can install directly from your GitHub repo.

- Latest from `main` branch:

```
pip install "taskscheduler @ git+https://github.com/CorreiaLuan/taskscheduler.git@main"
```

- With UI extras:

```
pip install "taskscheduler[ui] @ git+https://github.com/CorreiaLuan/taskscheduler.git@main"
```

- From a tagged release (recommended):

```
pip install "taskscheduler @ git+https://github.com/CorreiaLuan/taskscheduler.git@v0.1.0"
pip install "taskscheduler[ui] @ git+https://github.com/CorreiaLuan/taskscheduler.git@v0.1.0"
```

- Upgrade to latest:

```
pip install -U "taskscheduler @ git+https://github.com/CorreiaLuan/taskscheduler.git@main"
```

Repository URL: https://github.com/CorreiaLuan/taskscheduler.git
