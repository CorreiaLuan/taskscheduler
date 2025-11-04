from __future__ import annotations

import argparse
from datetime import datetime, time as dtime, date as ddate
from typing import List

from .core import PythonTask, TaskAlreadyExistsError, TaskNotFoundError, TaskError


def parse_time(value: str) -> dtime:
    # Accept HH:MM or H:MM
    return datetime.strptime(value, "%H:%M").time()


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Schedule Python scripts on Windows Task Scheduler")

    sub = p.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Create a new scheduled task")
    add.add_argument("--name", required=True)
    add.add_argument("--script", required=True)
    add.add_argument("--python", required=True, help="Path to python.exe to run the script")
    add.add_argument("--args", nargs=argparse.REMAINDER, help="Arguments passed to the script")
    add.add_argument("--frequency", choices=["Once", "Daily", "Weekly"], default="Daily")
    add.add_argument("--at", required=True, help="Time HH:MM (24h)")
    add.add_argument("--on", nargs="*", help="For Weekly: days of week; For Once: YYYY-MM-DD")
    add.add_argument("--description", default="Scheduled Python script")
    add.add_argument("--user", default=None)
    add.add_argument("--password", default=None)
    add.add_argument("--overwrite", action="store_true")

    dele = sub.add_parser("delete", help="Delete an existing task")
    dele.add_argument("--name", required=True)

    run = sub.add_parser("run", help="Run a task immediately")
    run.add_argument("--name", required=True)

    exists = sub.add_parser("exists", help="Check if a task exists")
    exists.add_argument("--name", required=True)

    args = p.parse_args(argv)

    try:
        if args.cmd == "add":
            at_t = parse_time(args.at)
            on_val = None
            if args.frequency == "Once":
                if args.on:
                    on_val = datetime.strptime(args.on[0], "%Y-%m-%d").date()
            elif args.frequency == "Weekly":
                on_val = args.on if args.on else None

            task = PythonTask(
                name=args.name,
                script=args.script,
                python=args.python,
                args=args.args or None,
                frequency=args.frequency,  # type: ignore
                at=at_t,
                on=on_val,
                description=args.description,
                user=args.user,
                password=args.password,
            )
            task.create(overwrite=args.overwrite)
            print(f"Task '{args.name}' created")
            return 0

        if args.cmd == "delete":
            # python/script not used for delete, pass placeholders
            from sys import executable as _py
            PythonTask(name=args.name, script="", python=_py).delete()
            print(f"Task '{args.name}' deleted")
            return 0

        if args.cmd == "run":
            from sys import executable as _py
            PythonTask(name=args.name, script="", python=_py).run()
            print(f"Task '{args.name}' started")
            return 0

        if args.cmd == "exists":
            from sys import executable as _py
            exists_b = PythonTask(name=args.name, script="", python=_py).exists()
            print("yes" if exists_b else "no")
            return 0 if exists_b else 1

    except (TaskError, ValueError) as e:
        print(str(e))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
