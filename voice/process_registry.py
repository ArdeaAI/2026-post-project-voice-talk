"""Tracks every subprocess we spawn so a Ctrl-C, crash, or terminal close
kills them all — not just the direct Python parent.

Any code that spawns a subprocess (currently `voice/llama_server.py` and
`voice/demos/moshi_e2e.py`) does three things:

  1. Calls `asyncio.create_subprocess_exec(..., start_new_session=True)` so
     the child gets its own process group — required to use os.killpg() to
     take out the child *and* any of its children in one call.
  2. Calls `register(proc)` immediately after spawn.
  3. Calls `unregister(proc)` after a clean shutdown (so we don't try to
     kill an already-reaped pid later).

The first call to `install_handlers()` from `main()` wires SIGINT, SIGTERM,
SIGHUP, and `atexit` to `kill_all()`. After that, no matter how the parent
process dies, every registered child gets SIGTERM then SIGKILL.

Why this matters: when llama-cpp-python's HTTP server or moshi-mlx's local
client traps SIGINT for its own purposes, a single Ctrl-C in the terminal
isn't always enough. We follow up with SIGKILL on a short timeout so audio
devices and GPU memory are released promptly.
"""

from __future__ import annotations

import asyncio
import atexit
import os
import signal
import time
from typing import Set

_processes: Set[asyncio.subprocess.Process] = set()
_handlers_installed = False
_kill_in_progress = False


def register(proc: asyncio.subprocess.Process) -> None:
    """Track a subprocess so signal handlers can kill it later."""
    _processes.add(proc)


def unregister(proc: asyncio.subprocess.Process) -> None:
    """Stop tracking after a clean shutdown."""
    _processes.discard(proc)


def _killpg_or_kill(proc: asyncio.subprocess.Process, sig: int) -> None:
    """Send `sig` to the child's process group, falling back to direct kill."""
    if proc.returncode is not None:
        return
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, OSError):
        return
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, OSError):
        try:
            if sig == signal.SIGKILL:
                proc.kill()
            else:
                proc.terminate()
        except (ProcessLookupError, OSError):
            pass


def kill_all(grace_seconds: float = 1.0) -> None:
    """Synchronously kill every registered subprocess.

    Safe to call from a signal handler. Sends SIGTERM to each process group,
    waits up to `grace_seconds`, then SIGKILLs survivors.
    """
    global _kill_in_progress
    if _kill_in_progress:
        return
    _kill_in_progress = True

    if not _processes:
        return

    procs = [p for p in _processes if p.returncode is None]

    for proc in procs:
        _killpg_or_kill(proc, signal.SIGTERM)

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if all(p.returncode is not None for p in procs):
            break
        for proc in procs:
            if proc.returncode is None:
                try:
                    pid, status = os.waitpid(proc.pid, os.WNOHANG)
                    if pid != 0:
                        try:
                            transport = proc._transport  # type: ignore[attr-defined]
                            transport._returncode = (
                                os.WEXITSTATUS(status)
                                if os.WIFEXITED(status)
                                else -1
                            )
                        except AttributeError:
                            pass
                except (ChildProcessError, OSError):
                    pass
        time.sleep(0.05)

    for proc in procs:
        if proc.returncode is None:
            _killpg_or_kill(proc, signal.SIGKILL)

    for proc in procs:
        if proc.returncode is None:
            try:
                os.waitpid(proc.pid, os.WNOHANG)
            except (ChildProcessError, OSError):
                pass


def _signal_handler(signum, frame):  # type: ignore[no-untyped-def]
    """Kill children, then re-raise so the process exits with the right status."""
    kill_all()
    try:
        signal.signal(signum, signal.SIG_DFL)
    except (OSError, ValueError):
        pass
    try:
        os.kill(os.getpid(), signum)
    except (OSError, ProcessLookupError):
        pass


def install_handlers() -> None:
    """Wire SIGINT/SIGTERM/SIGHUP and atexit to kill_all(). Idempotent."""
    global _handlers_installed
    if _handlers_installed:
        return
    _handlers_installed = True

    atexit.register(kill_all)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, _signal_handler)
        except (OSError, ValueError):
            pass


def registered_count() -> int:
    """How many subprocesses are currently tracked. For tests/diagnostics."""
    return sum(1 for p in _processes if p.returncode is None)
