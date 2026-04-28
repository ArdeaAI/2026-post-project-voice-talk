"""Demo 4 — Hume EVI 3 conversational session with live emotion readout.

Uses the standalone Hume Python SDK (not Pipecat's Hume TTS-only wrapper)
because we want the full EVI conversational flow with prosody scores. The
SDK's `MicrophoneInterface` handles mic-in / speaker-out, so all we own is
the WebSocket message callback and the live emotion display.
"""

from __future__ import annotations

import asyncio

from voice.menu import run_demo_with_ui, show_panel_until_escape
from voice.settings import Settings


async def run(settings: Settings) -> None:
    if not settings.has_hume:
        await show_panel_until_escape(
            title="Hume EVI 3 · keys missing",
            body_lines=[
                ("class:error", "HUME_API_KEY / HUME_SECRET_KEY missing."),
                ("class:body", "Set both in .env and re-launch."),
                ("class:muted", "Get keys at https://platform.hume.ai/settings/keys"),
            ],
        )
        return

    try:
        from hume import AsyncHumeClient, MicrophoneInterface, Stream  # noqa: F401
    except ImportError as e:
        await show_panel_until_escape(
            title="Hume EVI 3 · import failed",
            body_lines=[
                ("class:error", f"hume SDK import failed: {e}"),
                ("class:body", "Run `uv sync` to reinstall deps."),
            ],
        )
        return

    await run_demo_with_ui(
        title="Hume EVI 3 · emotion-aware conversation",
        demo_coro=lambda ui: _run_hume_session(settings, ui),
        initial_lines=[
            ("class:body", "Connecting to Hume EVI 3..."),
        ],
    )


async def _run_hume_session(settings: Settings, ui) -> None:  # type: ignore[no-untyped-def]
    from hume import AsyncHumeClient, MicrophoneInterface, Stream

    api_key = settings.HUME_API_KEY
    secret_key = settings.HUME_SECRET_KEY
    assert api_key and secret_key  # guaranteed by has_hume above

    client = AsyncHumeClient(api_key=api_key)

    # Top-3 emotion line gets re-rendered on every prosody update
    state: dict[str, list[str]] = {"transcript": [], "emotions": []}

    def repaint() -> None:
        lines: list[tuple[str, str]] = []
        lines.append(("class:success", "Connected · speak naturally"))
        lines.append(("class:muted", "Top emotions update live as Hume detects prosody"))
        lines.append(("", ""))
        if state["emotions"]:
            lines.append(("class:accent", "Emotions: " + state["emotions"][-1]))
            lines.append(("", ""))
        lines.append(("class:primary", "Conversation:"))
        for ln in state["transcript"][-10:]:
            lines.append(("class:body", ln))
        ui.set_lines(lines)

    def on_message(message) -> None:  # type: ignore[no-untyped-def]
        # Hume sends a discriminated union of message types. Pull out what we
        # care about (assistant/user text + prosody scores) and ignore the rest.
        try:
            msg_type = getattr(message, "type", None)

            # Text content from the conversation
            inner = getattr(message, "message", None)
            if inner is not None:
                role = getattr(inner, "role", None)
                content = getattr(inner, "content", None)
                if role and content:
                    role_label = "you " if role == "user" else "ai  "
                    state["transcript"].append(f"{role_label}: {content[:140]}")

            # Prosody scores — top-3 emotions
            models = getattr(message, "models", None)
            if models is not None:
                prosody = getattr(models, "prosody", None)
                if prosody is not None:
                    scores = getattr(prosody, "scores", None)
                    if scores:
                        # `scores` is a dict-like of emotion -> float
                        try:
                            items = scores.items() if hasattr(scores, "items") else []
                        except Exception:
                            items = []
                        top = sorted(items, key=lambda kv: -kv[1])[:3]
                        if top:
                            state["emotions"].append(
                                " · ".join(f"{name} {value:.2f}" for name, value in top)
                            )

            if msg_type == "error":
                err = getattr(message, "message", "")
                state["transcript"].append(f"err : {err}")

            repaint()
        except Exception as exc:  # don't let a parse error kill the session
            state["transcript"].append(f"warn: callback {exc!r}")
            repaint()

    try:
        async with client.empathic_voice.chat.connect(
            api_key=api_key,
            secret_key=secret_key,
        ) as socket:
            socket.set_on_message_callback(on_message)
            ui.set_lines(
                [
                    ("class:success", "Connected. Start speaking."),
                    ("class:muted", "Esc returns to the menu and closes the EVI session."),
                ]
            )

            byte_stream: Stream[bytes] = Stream.new()  # type: ignore[type-arg]

            mic_task = asyncio.create_task(
                MicrophoneInterface.start(
                    socket=socket,
                    byte_stream=byte_stream,
                    allow_user_interrupt=True,
                )
            )
            stop_task = asyncio.create_task(ui.stop.wait())

            done, pending = await asyncio.wait(
                {mic_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        ui.set_lines(
            [
                ("class:error", f"Hume session failed: {exc}"),
                ("class:muted", "Check HUME_API_KEY/HUME_SECRET_KEY and network egress to api.hume.ai."),
            ]
        )
        await ui.stop.wait()
