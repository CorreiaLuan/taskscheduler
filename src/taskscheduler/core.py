from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, time, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union, Literal, Any, Dict


class TaskError(Exception):
    pass


class TaskAlreadyExistsError(TaskError):
    pass


class TaskNotFoundError(TaskError):
    pass


def _to_path_str(p: Union[str, Path]) -> str:
    return str(Path(p).expanduser().resolve())


def _quote_ps_arg(value: str) -> str:
    # PowerShell uses double quotes; double them inside
    return '"' + value.replace('"', '""') + '"'


def _run_powershell(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True,
        capture_output=True,
        check=False,
    )


Frequency = Literal["Once", "Daily", "Weekly"]


@dataclass
class PythonTask:
    """
    Represents a Windows Scheduled Task that runs a Python script.

    Parameters
    - name: Task name in Task Scheduler.
    - script: Path to the Python script to execute.
    - python: Path to Python executable to run the script.
    - args: Extra arguments passed to the script.
    - frequency: One of "Once", "Daily", or "Weekly".
    - at: Time of day (HH:MM) or datetime.time.
    - on: For "Once", a date; for "Weekly", optional days of week (Mon..Sun). If omitted for Weekly, uses current weekday.
    - description: Task description.
    - user: Optional username to run the task as. If provided with password, runs regardless of logon.
    - password: Password for the specified user. If omitted, the task may prompt or run only when user is logged in.
    """

    name: str
    script: Union[str, Path]
    python: Union[str, Path]
    args: Sequence[str] | None = None
    frequency: Frequency = "Daily"
    at: Union[str, time] = time(12, 0)
    on: Optional[Union[date, Iterable[str]]] = None
    description: str = "Scheduled Python script"
    user: Optional[str] = None
    password: Optional[str] = None

    def _build_action(self) -> str:
        py = _to_path_str(self.python)
        script = _to_path_str(self.script)

        # Build arguments string: quote script path and each argument safely
        arg_parts: List[str] = [script]
        if self.args:
            arg_parts.extend(self.args)
        # Join and let PowerShell receive it as a single argument string
        # Use shlex.join on POSIX-like quoting for clarity, then strip quotes for PS and quote overall
        # Instead, we will quote each with PowerShell-style quoting
        ps_args = " ".join(_quote_ps_arg(str(a)) for a in arg_parts)

        return f"$action = New-ScheduledTaskAction -Execute {_quote_ps_arg(py)} -Argument {ps_args}"

    def _build_trigger(self) -> str:
        # Normalize time to HH:mm
        if isinstance(self.at, time):
            at_str = self.at.strftime("%H:%M")
        else:
            at_str = str(self.at)

        freq = self.frequency
        if freq == "Once":
            run_date = None
            if isinstance(self.on, date):
                run_date = self.on
            else:
                run_date = datetime.now().date()
            # Combine date and time to a single DateTime in PowerShell
            dt_str = f"{run_date.strftime('%Y-%m-%d')} {at_str}"
            return (
                f"$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date {_quote_ps_arg(dt_str)})"
            )
        elif freq == "Weekly":
            days = None
            if self.on:
                if isinstance(self.on, Iterable):
                    days = ",".join(self.on)
            if not days:
                # Default to current weekday name matching PowerShell DayOfWeek values
                days = datetime.now().strftime("%A")
            return (
                f"$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek {days} -At {at_str}"
            )
        else:  # Daily
            return f"$trigger = New-ScheduledTaskTrigger -Daily -At {at_str}"

    def _build_register(self) -> str:
        desc = _quote_ps_arg(self.description)
        name = _quote_ps_arg(self.name)
        base = (
            f"$description = {desc}; $taskName = {name}; "
            f"{self._build_action()}; {self._build_trigger()}; "
        )

        if self.user and self.password:
            user_q = _quote_ps_arg(self.user)
            pass_q = _quote_ps_arg(self.password)
            return (
                base
                + "Register-ScheduledTask -TaskName $taskName -Description $description "
                + "-Action $action -Trigger $trigger -User "
                + f"{user_q} -Password {pass_q} | Out-Null"
            )
        elif self.user:
            user_q = _quote_ps_arg(self.user)
            return (
                base
                + "Register-ScheduledTask -TaskName $taskName -Description $description "
                + f"-Action $action -Trigger $trigger -User {user_q} | Out-Null"
            )
        else:
            return (
                base
                + "Register-ScheduledTask -TaskName $taskName -Description $description -Action $action -Trigger $trigger | Out-Null"
            )

    def exists(self) -> bool:
        script = (
            f"$ErrorActionPreference='SilentlyContinue'; Get-ScheduledTask -TaskName {_quote_ps_arg(self.name)} | Out-Null; "
            f"if ($?) {{ exit 0 }} else {{ exit 1 }}"
        )
        res = _run_powershell(script)
        return res.returncode == 0

    def create(self, overwrite: bool = False) -> None:
        if self.exists():
            if not overwrite:
                raise TaskAlreadyExistsError(f"Task '{self.name}' already exists")
            self.delete()

        script = self._build_register()
        res = _run_powershell(script)
        if res.returncode != 0:
            raise TaskError(
                f"Failed to register task '{self.name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
            )

    def delete(self) -> None:
        if not self.exists():
            raise TaskNotFoundError(f"Task '{self.name}' not found")
        script = f"Unregister-ScheduledTask -TaskName {_quote_ps_arg(self.name)} -Confirm:$false"
        res = _run_powershell(script)
        if res.returncode != 0:
            raise TaskError(
                f"Failed to delete task '{self.name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
            )

    def run(self) -> None:
        if not self.exists():
            raise TaskNotFoundError(f"Task '{self.name}' not found")
        script = f"Start-ScheduledTask -TaskName {_quote_ps_arg(self.name)}"
        res = _run_powershell(script)
        if res.returncode != 0:
            raise TaskError(
                f"Failed to start task '{self.name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
            )

    def enable(self) -> None:
        script = f"Enable-ScheduledTask -TaskName {_quote_ps_arg(self.name)}"
        res = _run_powershell(script)
        if res.returncode != 0:
            raise TaskError(
                f"Failed to enable task '{self.name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
            )

    def disable(self) -> None:
        script = f"Disable-ScheduledTask -TaskName {_quote_ps_arg(self.name)}"
        res = _run_powershell(script)
        if res.returncode != 0:
            raise TaskError(
                f"Failed to disable task '{self.name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
            )

    def stop(self) -> None:
        script = f"Stop-ScheduledTask -TaskName {_quote_ps_arg(self.name)} -Confirm:$false"
        res = _run_powershell(script)
        if res.returncode != 0:
            raise TaskError(
                f"Failed to stop task '{self.name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
            )


def list_tasks(
    *,
    only_python: bool = False,
    author: Optional[str] = None,
    name_contains: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return a list of scheduled tasks with common fields.

    Each item contains:
    - Name, Status, Triggers, NextRunTime, LastRunTime, LastRunResult,
      Author, Created, Description, Actions (list of {Command, Arguments, WorkingDirectory}).
    """
    ps = r'''
$ErrorActionPreference = 'SilentlyContinue'
$tasks = Get-ScheduledTask
$result = foreach ($t in $tasks) {
  try {
    $info = Get-ScheduledTaskInfo -TaskName $t.TaskName
    $xml = Export-ScheduledTask -TaskName $t.TaskName
    $doc = [xml]$xml
    $reg = $doc.Task.RegistrationInfo
    $author = $reg.Author
    if (-not $author -or $author -eq '') {
      try {
        $uid = $doc.Task.Principals.Principal.UserId
        if ($uid) {
          if ($uid -is [string] -and $uid.StartsWith('S-1-')) {
            $sid = New-Object System.Security.Principal.SecurityIdentifier($uid)
            $nt = $sid.Translate([System.Security.Principal.NTAccount])
            $author = $nt.Value
          } else {
            $author = [string]$uid
          }
        }
      } catch {
        # ignore, leave $author empty
      }
    }
    $actions = @()
    foreach ($exec in $doc.Task.Actions.Exec) {
      $actions += [pscustomobject]@{
        Command = $exec.Command
        Arguments = $exec.Arguments
        WorkingDirectory = $exec.WorkingDirectory
      }
    }
    $trigs = @()
    foreach ($node in $doc.Task.Triggers.ChildNodes) {
      $type = $node.Name
      $start = $node.StartBoundary
      $tstr = (Get-Date $start).ToString('dd/MM/yyyy HH:mm:ss')
      $timeOnly = (Get-Date $start).ToString('HH:mm')
      # Extract days of week if present
      $daysNode = $node.DaysOfWeek
      $daysText = $null
      if ($daysNode) { $daysText = ($daysNode.ChildNodes | ForEach-Object { $_.Name }) -join ', ' }
      if ($type -eq 'TimeTrigger') { $summary = "At $tstr (one time)" }
      elseif ($type -eq 'DailyTrigger') { $summary = "At $timeOnly every day" }
      elseif ($type -eq 'WeeklyTrigger') {
        if ($daysText) { $summary = "At $timeOnly on $daysText" } else { $summary = "At $timeOnly weekly" }
      }
      else { $summary = "$type at $tstr" }
      $trigs += $summary
    }
    $nextStr = if ($info.NextRunTime -and $info.NextRunTime -ne [datetime]::MinValue) { $info.NextRunTime.ToString('dd/MM/yyyy HH:mm:ss') } else { '' }
    $lastStr = if ($info.LastRunTime -and $info.LastRunTime -ne [datetime]::MinValue) { $info.LastRunTime.ToString('dd/MM/yyyy HH:mm:ss') } else { '' }
    [pscustomobject]@{
      Name = $t.TaskName
      Status = $t.State
      NextRunTime = $nextStr
      LastRunTime = $lastStr
      LastRunResult = $info.LastTaskResult
      Author = $author
      Created = $reg.Date
      Description = $reg.Description
      Triggers = ($trigs -join '; ')
      Actions = $actions
    }
  } catch {
    continue
  }
}
$result | ConvertTo-Json -Depth 8
'''
    res = _run_powershell(ps)
    if res.returncode != 0:
        raise TaskError(f"Failed to list tasks: {res.stderr.strip()}\n{res.stdout.strip()}")
    import json

    txt = res.stdout.strip()
    if not txt:
        return []
    data = json.loads(txt)
    if isinstance(data, dict):
        data = [data]

    # Human-friendly formatting/mapping
    def map_status(s: Any) -> str:
        # Map both string and numeric states. Numeric values align with TaskScheduler's TASK_STATE:
        # 0=Unknown, 1=Disabled, 2=Queued, 3=Ready, 4=Running
        mapping = {
            "Ready": "🟢 Ready",
            "Running": "▶️ Running",
            "Disabled": "🟡 Disabled",
            "Queued": "⏳ Queued",
            "Unknown": "❓ Unknown",
            0: "❓ Unknown",
            1: "🟡 Disabled",
            2: "⏳ Queued",
            3: "🟢 Ready",
            4: "▶️ Running",
        }
        # Normalize possible numeric-as-string states
        try:
            if isinstance(s, str) and s.isdigit():
                s_val: Any = int(s)
            else:
                s_val = s
        except Exception:
            s_val = s
        return mapping.get(s_val, str(s))

    def map_result(code: Any) -> str:
        # Common Task Scheduler codes
        known = {
            0: "Succeeded",
            267009: "Running",
            267008: "Queued",
            267011: "Not executed yet",
            267002: "Disabled",
            267010: "Ready",
            267000: "No more runs",
        }
        try:
            if isinstance(code, str) and code.isdigit():
                code_int = int(code)
            elif isinstance(code, (int,)):
                code_int = code
            else:
                return str(code)
        except Exception:
            return str(code)
        return known.get(code_int, f"Code {code_int}")

    def _is_python_action(act: Dict[str, Any]) -> bool:
        cmd = str((act or {}).get("Command") or "").lower()
        args = str((act or {}).get("Arguments") or "").lower()
        return (
            cmd.endswith("python.exe")
            or "\\python" in cmd
            or "/python" in cmd
            or args.endswith(".py")
            or ".py " in args
        )

    def _passes_filters(item: Dict[str, Any]) -> bool:
        if author and str(item.get("Author") or "").lower() != author.lower():
            return False
        if name_contains and name_contains.lower() not in str(item.get("Name") or "").lower():
            return False
        if only_python:
            acts = item.get("Actions") or []
            if not any(_is_python_action(a) for a in acts):
                return False
        return True

    for it in data:
        it["Status"] = map_status(it.get("Status"))
        it["LastRunResult"] = map_result(it.get("LastRunResult"))

    return [it for it in data if _passes_filters(it)]


def list_python_tasks(**kwargs: Any) -> List[Dict[str, Any]]:
    """Convenience wrapper for listing only Python-executed tasks.

    Accepts the same keyword filters as list_tasks (author, name_contains).
    """
    kwargs.pop("only_python", None)
    return list_tasks(only_python=True, **kwargs)


def run_task(name: str) -> None:
    script = f"Start-ScheduledTask -TaskName {_quote_ps_arg(name)}"
    res = _run_powershell(script)
    if res.returncode != 0:
        raise TaskError(
            f"Failed to start task '{name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
        )


def enable_task(name: str) -> None:
    script = f"Enable-ScheduledTask -TaskName {_quote_ps_arg(name)}"
    res = _run_powershell(script)
    if res.returncode != 0:
        raise TaskError(
            f"Failed to enable task '{name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
        )


def disable_task(name: str) -> None:
    script = f"Disable-ScheduledTask -TaskName {_quote_ps_arg(name)}"
    res = _run_powershell(script)
    if res.returncode != 0:
        raise TaskError(
            f"Failed to disable task '{name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
        )


def stop_task(name: str) -> None:
    script = f"Stop-ScheduledTask -TaskName {_quote_ps_arg(name)} -Confirm:$false"
    res = _run_powershell(script)
    if res.returncode != 0:
        raise TaskError(
            f"Failed to stop task '{name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
        )


def delete_task(name: str) -> None:
    script = f"Unregister-ScheduledTask -TaskName {_quote_ps_arg(name)} -Confirm:$false"
    res = _run_powershell(script)
    if res.returncode != 0:
        raise TaskError(
            f"Failed to delete task '{name}':\n{res.stderr.strip()}\n{res.stdout.strip()}"
        )
