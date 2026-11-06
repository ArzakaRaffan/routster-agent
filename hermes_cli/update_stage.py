"""Stage updates to a desktop hand-off UI, if one is watching.

The desktop-update shim (scripts/desktop-update/posix.sh) renders update
progress from a status JSON file. The shim only writes stages it gates on
itself; the takeover children (_update_takeover.py, update_finish.py and the
PM sync / build stages they drive) can run for minutes with nothing on
screen. These helpers let long stages publish through the same file so the
window keeps moving.

Two discovery paths, because the status file's name embeds the shim's pid:

- ``HERMES_UPDATE_STATUS_FILE``: exported by the current posix.sh — covers
  new-shim → new-children directly.
- Marker fallback: an OLD shim (pre-env-var checkout, i.e. every old→new
  update) never exports the path, but it writes the marker whose first line
  is its own pid, and its status file is deterministic:
  ``${TMPDIR:-/tmp}/hermes-update-status.<pid>``.

Stdlib-only (importable under ``-I -S -B``) and never raises: a missing/
stale/unwritable file means no UI, which is exactly the pre-shim behavior —
a progress hiccup must never fail an update.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

STATUS_FILE_ENV = "HERMES_UPDATE_STATUS_FILE"
UI_SPAWNED_ENV = "HERMES_UPDATE_UI_ACTIVE"
MARKER_NAME = ".hermes-update-in-progress"


def _process_home() -> Path:
    """The marker and the shim's log live in the PROCESS home (update_lock.update_marker_path):
    the shim resolved ``$HERMES_HOME`` or the platform default, never a profile override, and
    the platform default (sudo invoker, data-dir suffix) is not ``~/.hermes`` everywhere."""
    from hermes_constants import get_process_hermes_home
    return get_process_hermes_home()


def status_file() -> Path | None:
    """The watching shim's status file, or None when no UI is discoverable."""
    exported = os.environ.get(STATUS_FILE_ENV, "").strip()
    if exported:
        return Path(exported)
    return _status_from_marker()


def _status_from_marker() -> Path | None:
    """Derive the shim's status file from the update marker's owner pid.

    The marker's first line is the hand-off shim's ``$$`` (update_lock.py
    adopts rather than rewrites it, so it still names the shim here). The
    shim's status file lives beside it, pid-suffixed. No marker (plain CLI
    update) or no matching file → no UI.
    """
    try:
        pid = int((_process_home() / MARKER_NAME).read_text(encoding="utf-8-sig")
                  .splitlines()[0].strip())
    except (OSError, ValueError, IndexError):
        return None
    if pid <= 0:
        return None
    # The shim writes beside ${TMPDIR:-/tmp}; gettempdir() resolves the same way.
    candidate = Path(tempfile.gettempdir()) / f"hermes-update-status.{pid}"
    return candidate if candidate.is_file() else None


def publish_stage(message: str) -> None:
    """Report a running stage to the watching UI. Best-effort, never raises.

    Only ever writes ``status=running``: terminal states belong to the shim,
    which publishes them after this process has exited. The atomic replace
    mirrors the shim's write_status — a polling reader must never observe a
    half-written file.
    """
    _render_stage_milestone(message)  # interactive terminal bar (independent of any desktop UI)
    path = status_file()
    if path is None:
        return
    payload = json.dumps({"status": "running", "message": message})
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".update-stage-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except OSError:
        pass


# === Interactive terminal progress (route-node bar) =========================
# An interactive `routster update` sets ROUTSTER_UPDATE_TTY=1; the completion
# child inherits it AND the terminal stdout (run_completion spawns with
# stdout=None), so hooking publish_stage here advances one bar across both
# processes. Every other context — the desktop shim, captured subprocesses,
# non-update builds — has the env unset or a non-tty stdout and renders
# nothing. Stdlib-only and never raises: a progress hiccup must not fail an update.

TTY_ENV = "ROUTSTER_UPDATE_TTY"
_last_pct = -1

# message substring -> (monotonic percent, label). First match wins.
_MILESTONES = (
    ("download", 12, "pulling the latest"),
    ("python dep", 45, "rebuilding the runtime"),
    ("dependenc", 45, "rebuilding the runtime"),
    ("building", 74, "building the apps"),
    ("packaging", 74, "building the apps"),
    ("webapp", 74, "building the apps"),
    ("web ui", 74, "building the apps"),
    ("tui", 74, "building the apps"),
    ("restart", 92, "restarting the gateway"),
)


def _tty_enabled() -> bool:
    import sys
    if os.environ.get(TTY_ENV) != "1" or os.environ.get("NO_COLOR"):
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def render_route(pct: int, label: str) -> None:
    """Print one monotonic route-node line to the terminal. Best-effort, never raises."""
    global _last_pct
    import sys
    if not _tty_enabled():
        return
    try:
        pct = 100 if pct > 100 else 0 if pct < 0 else int(pct)
        if pct <= _last_pct:
            return
        _last_pct = pct
        g, a, d, r = "\033[38;5;220m", "\033[1;38;5;214m", "\033[2m", "\033[0m"
        n = 6
        idx = round(pct / 100 * n) or 1
        done = pct >= 100
        parts = []
        for k in range(1, n + 1):
            if k > 1:
                parts.append(f"{g}━━{r}" if k <= idx else f"{d}┄┄{r}")
            if done or k < idx:
                parts.append(f"{g}●{r}")
            elif k == idx:
                parts.append(f"{a}◆{r}")
            else:
                parts.append(f"{d}○{r}")
        mark = f"{a}✦{r}" if done else f"{a}▸{r}"
        sys.stdout.write(f"  {''.join(parts)}  {g}{pct:>3}%{r}  {mark} {d}{label}{r}\n")
        sys.stdout.flush()
    except Exception:
        pass


def _render_stage_milestone(message: str) -> None:
    low = (message or "").lower()
    for key, pct, label in _MILESTONES:
        if key in low:
            render_route(pct, label)
            return


def _ui_present_in_log(log_text: str) -> bool:
    """True when THIS hand-off run started a browser/panel window.

    Reads the shim's own log lines from the tail (the run's shim logs 'shim:
    app window …' or 'shim: status panel pid=…' when a renderer exists,
    '… skipping UI' when it does not). Unparseable → False: spawning a
    duplicate panel is cosmetic; leaving a Safari user with no UI at all is
    the bug being fixed.
    """
    tail = "\n".join(log_text.splitlines()[-40:])
    return "app window" in tail or "status panel pid=" in tail


def ensure_panel(update_root: Path) -> None:
    """Pop the native status panel when no renderer is up (macOS, old→new).

    An old shim has no panel of its own and skipped its browser window on a
    non-Chromium default — its whole update then runs invisible. The freshly
    pulled tree ships update-panel.js, so the takeover child can
    start it against the discovered status file. Best-effort end to end: any
    failure leaves the update running exactly as UI-less as before.
    """
    if os.environ.get(UI_SPAWNED_ENV) or os.name != "posix" or os.uname().sysname != "Darwin":
        return
    if status_file() is None:
        return
    panel = update_root / "scripts" / "desktop-update" / "update-panel.js"
    if not panel.is_file():
        return
    try:
        log = _process_home() / "logs" / "desktop-update-handoff.log"
        if log.is_file() and _ui_present_in_log(log.read_text(encoding="utf-8-sig", errors="replace")[-8000:]):
            return
        import subprocess

        # Own session + devnull stdio: the panel must outlive this child the
        # same way the shim-spawned UI outlives the shim's stages, and it
        # self-exits when the shim publishes a terminal state.
        subprocess.Popen(
            ["/usr/bin/osascript", "-l", "JavaScript", str(panel), str(status_file())],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            # detached-spawn: ok — update progress panel, self-exits on the terminal state
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        os.environ[UI_SPAWNED_ENV] = "1"  # inherited: never spawn twice per chain
    except OSError:
        pass
