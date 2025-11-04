from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from streamlit.web import cli as stcli  # type: ignore
    except Exception as e:  # pragma: no cover
        print("Streamlit is not installed. Install with: pip install '.[ui]' ")
        return 1

    import taskscheduler.ui_app as app  # noqa: F401
    script_path = Path(app.__file__).resolve()
    sys.argv = [
        "streamlit",
        "run",
        str(script_path),
        "--",
    ]
    return stcli.main()  # type: ignore


if __name__ == "__main__":
    raise SystemExit(main())

