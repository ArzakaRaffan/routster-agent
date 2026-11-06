"""Routster pins HERMES_HOME on itself, so its children carry it and an unpinned process is Hermes's."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cli_entry_pins_the_routster_home_when_unset(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "HERMES_HOME"}
    env.update(HOME=str(tmp_path), USERPROFILE=str(tmp_path), LOCALAPPDATA=str(tmp_path / "AppData" / "Local"))
    out = subprocess.run(
        [sys.executable, "-c", "import os, hermes_cli.main; print(os.environ['HERMES_HOME'])"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=True,
    ).stdout.strip().splitlines()[-1]
    expected = tmp_path / "AppData" / "Local" / "routster" if sys.platform == "win32" else tmp_path / ".routster"
    assert Path(out) == expected
