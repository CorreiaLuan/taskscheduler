from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from taskscheduler.core import (
    list_tasks,
    run_task,
    enable_task,
    disable_task,
    stop_task,
    delete_task,
    PythonTask,  # type: ignore
)


st.set_page_config(page_title="Python Tasks", layout="wide")
st.title("Windows Task Scheduler : Python UI")
st.caption("Browse and inspect scheduled tasks")


@st.cache_data(ttl=5)
def load_tasks(only_python: bool) -> List[Dict[str, Any]]:
    return list_tasks(only_python=only_python)


def get_tasks(only_python: bool) -> List[Dict[str, Any]]:
    """Return cached tasks from session state, only reloading when needed.
    Reload when filter changes or invalidate flag is set; otherwise reuse snapshot.
    """
    ss = st.session_state
    if (
        ss.get("tasks_snapshot") is None
        or ss.get("tasks_only_py") != only_python
        or ss.get("invalidate_tasks") is True
    ):
        ss["tasks_snapshot"] = load_tasks(only_python)
        ss["tasks_only_py"] = only_python
        ss["invalidate_tasks"] = False
    return ss["tasks_snapshot"]


col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.4])
with col1:
    if st.button("Refresh", type="primary"):
        st.session_state["invalidate_tasks"] = True
with col2:
    only_py = st.checkbox("Only Python tasks", value=True)

# Selected task stored in session state
selected_name: str | None = st.session_state.get("selected_task")

def _require_selection(action: str) -> str | None:
    if not st.session_state.get("selected_task"):
        st.warning(f"Select a task in the table to {action}.")
        return None
    return st.session_state["selected_task"]

with col3:
    if st.button("Run", use_container_width=True, icon="▶️"):
        name = _require_selection("run")
        if name:
            try:
                run_task(name)
                st.success(f"Started '{name}'")
                st.session_state["invalidate_tasks"] = True
            except Exception as e:
                st.error(str(e))
with col4:
    if st.button("Enable", use_container_width=True, icon="✅"):
        name = _require_selection("enable")
        if name:
            try:
                enable_task(name)
                st.success(f"Enabled '{name}'")
                st.session_state["invalidate_tasks"] = True
            except Exception as e:
                st.error(str(e))
with col5:
    if st.button("Disable", use_container_width=True, icon="🚫"):
        name = _require_selection("disable")
        if name:
            try:
                disable_task(name)
                st.success(f"Disabled '{name}'")
                st.session_state["invalidate_tasks"] = True
            except Exception as e:
                st.error(str(e))
with col6:
    if st.button("End", use_container_width=True, icon="⏹️"):
        name = _require_selection("stop")
        if name:
            try:
                stop_task(name)
                st.success(f"Stopped '{name}'")
                st.session_state["invalidate_tasks"] = True
            except Exception as e:
                st.error(str(e))

with col7:
    if st.button("Delete", use_container_width=True, icon="🗑️"):
        name = _require_selection("delete")
        if name:
            st.session_state["confirm_delete_name"] = name

with col8:
    if st.button("Add", use_container_width=True, icon="➕"):
        st.session_state["show_add_form"] = True

# --- Dialog helpers ---------------------------------------------------------

def _render_add_form_body() -> None:
    name = st.text_input("Name", placeholder="my-task")
    colp1, colp2 = st.columns(2)
    with colp1:
        python = st.text_input("Python executable (required)", value="", placeholder=r"C:\\Path\\To\\Python\\python.exe")
    with colp2:
        script = st.text_input("Python script (required)", value="", placeholder=r"C:\\path\\to\\job.py")

    args_txt = st.text_input("Args (optional)", value="", placeholder="--foo 123 --bar")
    frequency = st.selectbox("Frequency", options=["Once", "Daily", "Weekly"], index=1)
    time_mode = st.radio("Time input mode", options=["Pick", "Manual"], horizontal=True)
    at_value = None
    if time_mode == "Pick":
        at_value = st.time_input("At (time)")
    else:
        at_text = st.text_input("At (time) [HH:MM or HH:MM:SS]", placeholder="12:00")
        at_text = (at_text or "").strip()
        # Basic validation
        import re as _re
        if at_text and not _re.match(r"^([01]\\d|2[0-3]):[0-5]\\d(:[0-5]\\d)?$", at_text):
            st.warning("Time format should be HH:MM or HH:MM:SS")
        at_value = at_text

    on_date = None
    on_days: List[str] | None = None
    if frequency == "Once":
        on_date = st.date_input("On (date)")
    elif frequency == "Weekly":
        on_days = st.multiselect("On (days)", options=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]) or None

    description = st.text_input("Description", value="Scheduled Python script")
    colu1, colu2 = st.columns(2)
    with colu1:
        user = st.text_input("User (optional)", value="")
    with colu2:
        password = st.text_input("Password (optional)", type="password", value="")
    overwrite = st.checkbox("Overwrite if exists", value=False)

    col_ok, col_cancel = st.columns([1,1])
    with col_ok:
        create_clicked = st.button("Create", type="primary", use_container_width=True)
    with col_cancel:
        cancel_clicked = st.button("Cancel", use_container_width=True)

    if cancel_clicked:
        st.session_state["show_add_form"] = False
        st.rerun()

    if create_clicked:
        if not name or not python or not script:
            st.error("Name, Python and Script are required.")
        else:
            try:
                import shlex as _shlex
                args_list = _shlex.split(args_txt) if args_txt.strip() else None
            except Exception:
                args_list = None
            try:
                task = PythonTask(
                    name=name,
                    script=script,
                    python=python,
                    args=args_list,
                    frequency=frequency,  # type: ignore
                    at=at_value,
                    on=on_date or on_days,
                    description=description,
                    user=user or None,
                    password=password or None,
                )
                task.create(overwrite=overwrite)
                st.success(f"Task '{name}' created")
                st.session_state["show_add_form"] = False
                st.session_state["invalidate_tasks"] = True
                st.rerun()
            except Exception as e:
                st.error(str(e))


# Add dialog using Streamlit's modal API if available
_has_dialog = hasattr(st, "dialog")
if _has_dialog:
    @st.dialog("Add Scheduled Task", width="large")
    def _add_task_dialog():  # pragma: no cover
        _render_add_form_body()
else:
    def _add_task_dialog():
        st.subheader("Add Scheduled Task")
        _render_add_form_body()

if _has_dialog:
    @st.dialog("Confirm Delete")
    def _confirm_delete_dialog():  # pragma: no cover
        name = st.session_state.get("confirm_delete_name")
        if not name:
            return
        st.warning(f"Delete task '{name}'? This cannot be undone.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, delete", type="primary", use_container_width=True, icon="🗑️"):
                try:
                    delete_task(name)
                    st.success(f"Deleted '{name}'")
                    st.session_state["confirm_delete_name"] = None
                    st.session_state["selected_task"] = None
                    st.session_state["invalidate_tasks"] = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with col_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state["confirm_delete_name"] = None
                st.rerun()
else:
    def _confirm_delete_dialog():
        name = st.session_state.get("confirm_delete_name")
        if not name:
            return
        st.warning(f"Delete task '{name}'? This cannot be undone.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, delete", type="primary", use_container_width=True):
                try:
                    delete_task(name)
                    st.success(f"Deleted '{name}'")
                    st.session_state["confirm_delete_name"] = None
                    st.session_state["selected_task"] = None
                    st.session_state["invalidate_tasks"] = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with col_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state["confirm_delete_name"] = None
                st.rerun()

tasks = get_tasks(only_py)

if not tasks:
    st.info("No tasks found or access denied.")
    st.stop()

display_cols = [
    "Name",
    "Status",
    "Triggers",
    "NextRunTime",
    "LastRunTime",
    "LastRunResult",
    "Author",
]

rows: List[Dict[str, Any]] = []
for t in tasks:
    r = {k: t.get(k, "") for k in display_cols}
    rows.append(r)

df = pd.DataFrame(rows)

# Center all values via CSS
st.markdown(
    """
    <style>
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { text-align: center !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

selected = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    selection_mode="single-row",
    key='df_with_selection',
    on_select= "rerun"
)

# Determine selected row from session state (Streamlit stores selection by key)
new_selected: str | None = None
sel_state = st.session_state.get('df_with_selection')
try:
    # Possible formats depending on Streamlit version
    if isinstance(sel_state, dict):
        # Newer API may nest under 'selection' with 'rows'
        sel_info = sel_state.get('selection') or sel_state
        rows_sel = sel_info.get('rows') if isinstance(sel_info, dict) else None
        if isinstance(rows_sel, list) and rows_sel:
            idx = rows_sel[0]
            if isinstance(idx, int) and 0 <= idx < len(df):
                new_selected = str(df.iloc[idx]["Name"]).strip()
    elif sel_state is not None and hasattr(sel_state, 'rows'):
        rows_sel = getattr(sel_state, 'rows')
        if isinstance(rows_sel, list) and rows_sel:
            idx = rows_sel[0]
            if isinstance(idx, int) and 0 <= idx < len(df):
                new_selected = str(df.iloc[idx]["Name"]).strip()
except Exception:
    pass

if new_selected != selected_name:
    st.session_state["selected_task"] = new_selected
    selected_name = new_selected

if selected_name:
    st.subheader(f"Details: {selected_name}")
    full = next((t for t in tasks if str(t.get("Name")).strip() == selected_name), None)
    if full:
        with st.container(border=True):
            st.markdown("**Description**")
            st.write(full.get("Description") or "-")

            st.markdown("**Actions**")
            actions = full.get("Actions") or []
            if actions:
                st.table([{k: (v or "") for k, v in a.items()} for a in actions])
            else:
                st.write("No Exec actions found.")

if st.session_state.get("show_add_form"):
    _add_task_dialog()

if st.session_state.get("confirm_delete_name"):
    _confirm_delete_dialog()


