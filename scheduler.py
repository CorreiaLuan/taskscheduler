"""
Example entry point.

The project is packaged under `src/taskscheduler`.
Prefer installing locally with `pip install -e .` to make `taskscheduler` importable.
When running this file directly without installing, it falls back to adding `src/` to `sys.path`.
"""

from pathlib import Path
import sys

try:
    from taskscheduler import PythonTask
except ModuleNotFoundError:
    # Fallback for running this file directly without installing the package.
    import sys as _sys
    _src = (Path(__file__).resolve().parent / "src")
    if _src.exists():
        _sys.path.insert(0, str(_src))
        from taskscheduler import PythonTask  # type: ignore
    else:
        raise


def main() -> None:
    # Example: create a daily task at 12:00
    job = PythonTask(
        name="example-task",
        script=str((Path(__file__).parent / "example.py").resolve()),
        python=str(sys.executable),
        frequency="Daily",
        at="12:00",
        description="Example scheduled task",
    )
    try:
        job.create(overwrite=True)
        print("Task 'example-task' created.")
    except Exception as exc:  # keep simple since this is just a demo
        print(f"Failed to create task: {exc}")


if __name__ == "__main__":
    main()
