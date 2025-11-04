"""
Windows Task Scheduler helper for scheduling Python scripts via PowerShell.

Public API:
- PythonTask: create, run, delete, and check scheduled tasks.
"""

from .core import PythonTask, TaskAlreadyExistsError, TaskNotFoundError

__all__ = [
    "PythonTask",
    "TaskAlreadyExistsError",
    "TaskNotFoundError",
]

__version__ = "0.1.0"

