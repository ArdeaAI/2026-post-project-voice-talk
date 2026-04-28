"""Demo 2 — Kyutai Moshi end-to-end speech-native model.

Spawns `python -m moshi_mlx.local` as a child process via
asyncio.create_subprocess_exec (the safe variant — no shell). Moshi's bundled
client owns the audio devices directly (sounddevice + rustymimi codec) and
runs full-duplex. We surface its stdout/stderr in the live panel and kill the
subprocess on Esc.

The first launch downloads ~8GB of int8 weights from HuggingFace — that's
managed by moshi-mlx itself, not by `voice/models.py`.
"""

from __future__ import annotations

import asyncio
import sys

from voice.menu import run_demo_with_ui, show_panel_until_escape
from voice.process_registry import register, unregister
from voice.settings import Settings


async def run(settings: Settings) -> None:
    try:
        import moshi_mlx  # noqa: F401
    except ImportError as e:
        await show_panel_until_escape(
            title="Moshi · import failed",
            body_lines=[
                ("class:error", f"moshi-mlx import failed: {e}"),
                ("class:body", "Run `uv sync` to reinstall deps."),
                ("class:muted", "moshi-mlx requires Apple silicon (MLX backend)."),
            ],
        )
        return

    await run_demo_with_ui(
        title="Moshi · end-to-end speech-native (Kyutai)",
        demo_coro=lambda ui: _run_moshi_subprocess(settings, ui),
        initial_lines=[
            ("class:body", "Starting Moshi MLX subprocess..."),
            (
                "class:muted",
                "First launch downloads ~8GB of weights to ~/.cache/huggingface.",
            ),
        ],
    )


async def _run_moshi_subprocess(settings: Settings, ui) -> None:  # type: ignore[no-untyped-def]
    argv = [sys.executable, "-m", "moshi_mlx.local"]
    proc: asyncio.subprocess.Process | None = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,  # own process group for clean teardown
        )
        register(proc)
    except FileNotFoundError as e:
        ui.set_lines(
            [
                ("class:error", f"Failed to launch moshi-mlx: {e}"),
                ("class:body", "Try `uv run python -m moshi_mlx.local` directly."),
            ]
        )
        await ui.stop.wait()
        return

    ui.set_lines(
        [
            ("class:success", f"Moshi running (pid {proc.pid})"),
            (
                "class:muted",
                "Speak into your default mic — Moshi replies through your default speaker.",
            ),
            (
                "class:muted",
                "First-launch model download can take several minutes.",
            ),
            ("", ""),
            ("class:primary", "subprocess output:"),
        ]
    )

    async def _pump_output() -> None:
        assert proc is not None
        if proc.stdout is None:
            return
        try:
            async for raw_line in proc.stdout:
                try:
                    line = raw_line.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    line = repr(raw_line)
                if not line:
                    continue
                lower = line.lower()
                if "error" in lower or "traceback" in lower:
                    ui.append_line("class:error", line[:240])
                elif "warning" in lower:
                    ui.append_line("class:warning", line[:240])
                else:
                    ui.append_line("class:body", line[:240])
        except Exception as e:
            ui.append_line("class:warning", f"(stdout pump exited: {e})")

    pump_task = asyncio.create_task(_pump_output())
    stop_task = asyncio.create_task(ui.stop.wait())
    proc_task = asyncio.create_task(proc.wait())

    try:
        done, pending = await asyncio.wait(
            {pump_task, stop_task, proc_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        if proc.returncode is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
        unregister(proc)
        for t in (pump_task, proc_task):
            if not t.done():
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass

    if proc.returncode and proc.returncode != 0 and not ui.stop.is_set():
        ui.append_line(
            "class:error",
            f"moshi-mlx exited with code {proc.returncode}",
        )
        await ui.stop.wait()
