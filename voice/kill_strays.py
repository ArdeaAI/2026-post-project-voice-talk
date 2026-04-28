"""`voice kill` — emergency cleanup for orphaned subprocesses.

If anything *did* escape (a previous run was force-quit before the registry
could reap children, or you upgraded the package mid-demo, or whatever) this
finds and kills any python processes that look like they belong to us:

  - `python -m moshi_mlx.local`
  - `python -m llama_cpp.server`
  - any python from this repo's .venv whose argv mentions pipecat

Sends SIGTERM, waits a beat, then SIGKILL. Reports what it did.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from voice.console import console

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PATH = REPO_ROOT / ".venv"


def _ps_python_processes() -> list[tuple[int, str]]:
    """Return [(pid, argv), ...] for every python process visible to ps."""
    try:
        out = subprocess.check_output(
            ["ps", "-axo", "pid=,command="], text=True, errors="replace"
        )
    except Exception as exc:
        console.print(f"[error]ps failed: {exc}[/error]")
        return []

    rows: list[tuple[int, str]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        try:
            pid = int(head)
        except ValueError:
            continue
        rows.append((pid, rest))
    return rows


def _is_ours(argv: str) -> bool:
    if "moshi_mlx" in argv:
        return True
    if "llama_cpp.server" in argv or "llama_cpp/server" in argv:
        return True
    # Anything python running from our venv that mentions pipecat
    if str(VENV_PATH) in argv and "pipecat" in argv:
        return True
    # voice CLI itself (in case there's a stale interactive launch)
    if str(VENV_PATH) in argv and "voice." in argv:
        return True
    return False


def run_kill() -> int:
    console.rule("[primary]voice kill[/primary]")
    console.print("[muted]Searching for stray child processes...[/muted]")

    rows = _ps_python_processes()
    own_pid = os.getpid()
    targets = [
        (pid, argv)
        for pid, argv in rows
        if pid != own_pid and _is_ours(argv)
    ]

    if not targets:
        console.print("[success]✓ No stray processes found.[/success]")
        return 0

    console.print(f"\nFound [accent]{len(targets)}[/accent] target(s):")
    for pid, argv in targets:
        console.print(f"  [muted]pid {pid:>6}[/muted]  {argv[:140]}")
    console.print()

    # Round 1: SIGTERM
    for pid, _ in targets:
        try:
            os.kill(pid, signal.SIGTERM)
            console.print(f"  [warning]→[/warning] SIGTERM sent to pid {pid}")
        except ProcessLookupError:
            console.print(f"  [muted]–[/muted] pid {pid} already gone")
        except PermissionError:
            console.print(f"  [error]✗[/error] pid {pid}: permission denied")
        except Exception as exc:
            console.print(f"  [error]✗[/error] pid {pid}: {exc}")

    # Wait briefly for graceful shutdown
    time.sleep(1.5)

    # Round 2: SIGKILL anyone still alive
    survivors = []
    for pid, argv in targets:
        try:
            os.kill(pid, 0)  # signal 0 = "are you alive?"
        except ProcessLookupError:
            continue
        except PermissionError:
            survivors.append((pid, argv, "permission denied"))
            continue
        # Still alive — escalate
        try:
            os.kill(pid, signal.SIGKILL)
            console.print(f"  [error]→[/error] SIGKILL pid {pid}")
        except ProcessLookupError:
            pass
        except Exception as exc:
            survivors.append((pid, argv, str(exc)))

    if survivors:
        console.print()
        console.print("[error]Could not kill:[/error]")
        for pid, argv, why in survivors:
            console.print(f"  pid {pid}: {why}")
        return 1

    console.print()
    console.print("[success]✓ All targets reaped.[/success]")
    return 0


if __name__ == "__main__":
    sys.exit(run_kill())
