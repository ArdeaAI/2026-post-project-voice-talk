"""voice CLI entrypoint — referenced by `[project.scripts] voice` in pyproject.

Dispatches between the menu and the doctor subcommand. Heavy demo imports are
deferred via `resolve_runner` so the menu always opens fast.
"""

from __future__ import annotations

import asyncio
import sys

from voice.console import console
from voice.menu import DEMOS, resolve_runner, run_menu
from voice.settings import Settings


async def _main_loop() -> int:
    settings = Settings()

    while True:
        choice = await run_menu(settings)
        if choice == "quit":
            console.print("[muted]Bye.[/muted]")
            return 0

        entry = next((d for d in DEMOS if d.id == choice), None)
        if entry is None:
            console.print(f"[error]Unknown demo: {choice!r}[/error]")
            continue

        try:
            runner = resolve_runner(entry.runner_path)
            await runner(settings)
        except KeyboardInterrupt:
            # Esc / Ctrl-C inside a demo: clean return to menu
            pass
        except Exception:
            console.print_exception(show_locals=False)
            console.print()
            try:
                console.input(
                    "[muted]Press Enter to return to the menu...[/muted]"
                )
            except (KeyboardInterrupt, EOFError):
                return 1


def main() -> int:
    """Entry referenced by `[project.scripts] voice = voice.main:main`."""
    # Wire signal + atexit cleanup before doing anything else, so any
    # subprocess we spawn (llama-cpp server, moshi-mlx) dies with us no
    # matter how the parent exits — Ctrl-C, SIGTERM, SIGHUP, normal exit.
    from voice.process_registry import install_handlers
    install_handlers()

    args = sys.argv[1:]
    if args and args[0] == "doctor":
        from voice.doctor import run_doctor
        return run_doctor()
    if args and args[0] == "download":
        from voice.download import main_cli
        return main_cli()
    if args and args[0] == "kill":
        from voice.kill_strays import run_kill
        return run_kill()
    if args and args[0] in {"-h", "--help"}:
        console.print(
            "[primary]voice[/primary]                          launch the demo TUI\n"
            "[primary]voice doctor[/primary]                   pre-flight check (audio, keys, models)\n"
            "[primary]voice download [target...][/primary]     pre-fetch model weights\n"
            "[muted]                                  targets: llama, whisper, kokoro, moshi, all (default)[/muted]\n"
            "[primary]voice kill[/primary]                     reap stray child processes from a previous run\n"
        )
        return 0

    try:
        return asyncio.run(_main_loop())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
