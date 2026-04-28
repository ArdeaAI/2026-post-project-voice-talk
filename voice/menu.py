"""Full-screen prompt_toolkit TUI: demo picker plus the helper used by demo
stubs that just want to wait for Esc.

prompt_toolkit was chosen over Rich-only because Rich can't reliably trap Esc
inside a Live display. prompt_toolkit's Application + KeyBindings is the right
primitive for keyboard-driven full-screen UIs.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Awaitable, Callable

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from voice.settings import Settings

# Gruvbox-aligned prompt_toolkit style. Mirrors the slide deck's gruvbox.scss.
PT_STYLE = Style.from_dict(
    {
        "title": "fg:#fe8019 bold",
        "subtitle": "fg:#fabd2f",
        "body": "fg:#ebdbb2",
        "muted": "fg:#928374",
        "warning": "fg:#fabd2f",
        "error": "fg:#fb4934",
        "selected": "fg:#282828 bg:#fabd2f bold",
        "selected.sub": "fg:#3c3836 bg:#fabd2f",
        "available": "fg:#b8bb26",
        "unavailable": "fg:#928374 italic",
        "hint": "fg:#83a598",
        "border": "fg:#504945",
    }
)


@dataclass(frozen=True)
class DemoEntry:
    id: str
    title: str
    subtitle: str
    runner_path: str  # e.g. "voice.demos.local_pipeline:run"


DEMOS: tuple[DemoEntry, ...] = (
    DemoEntry(
        id="local_pipeline",
        title="Local pipeline",
        subtitle="Pipecat + Moonshine v2 + Kokoro + llama-cpp · Apache 2.0",
        runner_path="voice.demos.local_pipeline:run",
    ),
    DemoEntry(
        id="moshi_e2e",
        title="Moshi (end-to-end)",
        subtitle="Kyutai · speech-native · full duplex",
        runner_path="voice.demos.moshi_e2e:run",
    ),
    DemoEntry(
        id="api_comparison",
        title="API comparison",
        subtitle="OpenAI Realtime vs. local pipeline · side by side",
        runner_path="voice.demos.api_comparison:run",
    ),
    DemoEntry(
        id="hume_emotion",
        title="Hume EVI 3",
        subtitle="Explicit emotion modeling",
        runner_path="voice.demos.hume_emotion:run",
    ),
)


async def run_menu(settings: Settings) -> str:
    """Show the demo picker. Returns the chosen demo id, or 'quit'."""
    state = {"selected": 0}

    def is_available(entry: DemoEntry) -> bool:
        return not settings.missing_keys_for(entry.id)

    def render() -> FormattedText:
        lines: list[tuple[str, str]] = []
        lines.append(("class:title", "\n  voice CLI · Chattanooga AI Collective\n"))
        lines.append(
            ("class:muted", "  ↑↓ select   ⏎ launch   Esc / q quit\n\n")
        )

        for i, entry in enumerate(DEMOS):
            is_sel = i == state["selected"]
            avail = is_available(entry)

            cursor = "▸ " if is_sel else "  "

            if is_sel:
                title_style = "class:selected"
                sub_style = "class:selected.sub"
            elif avail:
                title_style = "class:body"
                sub_style = "class:muted"
            else:
                title_style = "class:unavailable"
                sub_style = "class:unavailable"

            lines.append((title_style, f"  {cursor}{entry.title}\n"))
            lines.append((sub_style, f"        {entry.subtitle}\n"))
            if not avail:
                missing = ", ".join(settings.missing_keys_for(entry.id))
                lines.append(("class:warning", f"        ⚠  needs {missing}\n"))
            lines.append(("", "\n"))

        return FormattedText(lines)

    kb = KeyBindings()

    @kb.add("up")
    def _up(event):  # noqa: ARG001
        state["selected"] = (state["selected"] - 1) % len(DEMOS)
        event.app.invalidate()

    @kb.add("down")
    def _down(event):  # noqa: ARG001
        state["selected"] = (state["selected"] + 1) % len(DEMOS)
        event.app.invalidate()

    @kb.add("enter")
    def _enter(event):
        entry = DEMOS[state["selected"]]
        if is_available(entry):
            event.app.exit(result=entry.id)

    @kb.add("escape")
    @kb.add("q")
    @kb.add("c-c")
    def _quit(event):
        event.app.exit(result="quit")

    layout = Layout(
        HSplit([Window(FormattedTextControl(render), wrap_lines=False)])
    )

    app: Application[str] = Application(
        layout=layout,
        key_bindings=kb,
        style=PT_STYLE,
        full_screen=True,
        mouse_support=False,
    )
    result = await app.run_async()
    return result or "quit"


async def show_panel_until_escape(
    title: str,
    body_lines: list[tuple[str, str]],
    footer: str = "Press Esc to return to the menu",
) -> None:
    """Render a static panel and wait until the user presses Esc.

    Used by demos that just want to display a message and wait. `body_lines`
    is a list of (style_class, text) tuples — same vocabulary as PT_STYLE.
    """

    def render() -> FormattedText:
        lines: list[tuple[str, str]] = []
        lines.append(("class:title", f"\n  {title}\n\n"))
        for style_class, text in body_lines:
            lines.append((style_class, f"  {text}\n"))
        lines.append(("", "\n"))
        lines.append(("class:hint", f"  {footer}\n"))
        return FormattedText(lines)

    kb = KeyBindings()

    @kb.add("escape")
    @kb.add("q")
    @kb.add("c-c")
    def _esc(event):
        event.app.exit()

    layout = Layout(HSplit([Window(FormattedTextControl(render))]))
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=PT_STYLE,
        full_screen=True,
        mouse_support=False,
    )
    await app.run_async()


class DemoUI:
    """Mutable UI handle passed into a live demo coroutine.

    The demo updates `set_lines()` / `append_line()` to display status; the
    surrounding Application redraws automatically. The `stop` asyncio.Event
    is set when the user presses Esc/q/Ctrl-C — demos should poll it (or use
    `await stop.wait()`) for graceful cancellation alongside their own work.
    """

    def __init__(self, app: Application, lines: list[tuple[str, str]], stop: "asyncio.Event") -> None:
        self._app = app
        self._lines = lines
        self.stop = stop

    def set_lines(self, lines: list[tuple[str, str]]) -> None:
        self._lines.clear()
        self._lines.extend(lines)
        self._invalidate()

    def append_line(self, style: str, text: str, max_lines: int = 24) -> None:
        self._lines.append((style, text))
        # Rolling window so the panel doesn't grow off-screen
        if len(self._lines) > max_lines:
            del self._lines[: len(self._lines) - max_lines]
        self._invalidate()

    def _invalidate(self) -> None:
        try:
            self._app.invalidate()
        except Exception:
            # The app may have already exited; harmless during teardown.
            pass


async def run_demo_with_ui(
    title: str,
    demo_coro: Callable[[DemoUI], Awaitable[None]],
    initial_lines: list[tuple[str, str]] | None = None,
) -> None:
    """Run a demo coroutine inside a live full-screen panel.

    The demo gets a `DemoUI` handle to update status text. The user can press
    Esc/q/Ctrl-C at any time to set `ui.stop` and tear the demo down. The
    coroutine is cancelled if it doesn't complete on its own when the panel
    exits — demos should treat asyncio.CancelledError as a clean exit.
    """
    import asyncio  # local import — keep module import-time cheap

    stop = asyncio.Event()
    lines: list[tuple[str, str]] = list(initial_lines or [])

    def render() -> FormattedText:
        out: list[tuple[str, str]] = []
        out.append(("class:title", f"\n  {title}\n\n"))
        for style_class, text in lines:
            out.append((style_class, f"  {text}\n"))
        out.append(("", "\n"))
        out.append(("class:hint", "  Press Esc to return to the menu\n"))
        return FormattedText(out)

    kb = KeyBindings()

    @kb.add("escape")
    @kb.add("q")
    @kb.add("c-c")
    def _esc(event):
        stop.set()
        event.app.exit()

    layout = Layout(HSplit([Window(FormattedTextControl(render))]))
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=PT_STYLE,
        full_screen=True,
        mouse_support=False,
    )

    ui = DemoUI(app=app, lines=lines, stop=stop)

    demo_task: asyncio.Task[None] = asyncio.create_task(demo_coro(ui))
    app_task: asyncio.Task[None] = asyncio.create_task(app.run_async())  # type: ignore[arg-type]

    try:
        # Whichever finishes first ends the demo.
        done, pending = await asyncio.wait(
            {demo_task, app_task}, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        stop.set()
        # If the demo coroutine is still running, cancel it.
        if not demo_task.done():
            demo_task.cancel()
            try:
                await demo_task
            except (asyncio.CancelledError, Exception):
                pass
        # If the application is still running (demo finished first), close it.
        if not app_task.done():
            try:
                app.exit()
            except Exception:
                pass
            try:
                await app_task
            except (asyncio.CancelledError, Exception):
                pass


def resolve_runner(runner_path: str) -> Callable[[Settings], Awaitable[None]]:
    """Lazy-import a 'pkg.mod:fn' coroutine path.

    Heavy imports (Pipecat, Moshi, etc.) are deferred until a demo is actually
    chosen, keeping menu cold-start under a second.
    """
    module_name, _, fn_name = runner_path.partition(":")
    if not module_name or not fn_name:
        raise ValueError(f"Bad runner_path: {runner_path!r}")
    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name)
    return fn
