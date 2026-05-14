"""Thin entry point that launches the Streamlit UI.

Installed as the `momo-gui` console script via `pyproject.toml`. Internally
delegates to `streamlit run` so users do not need to remember the full path
to the Streamlit app file.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from streamlit.web import cli as streamlit_cli
    except ImportError:  # pragma: no cover - optional dependency
        sys.stderr.write(
            "Streamlit 이 설치되어 있지 않습니다. 다음 명령으로 설치하세요:\n"
            "    pip install 'momo-meeting[gui]'\n"
        )
        return 1

    app_path = Path(__file__).resolve().with_name("streamlit_app.py")
    sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
    streamlit_cli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
