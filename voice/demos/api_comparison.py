"""Demo 3 — API comparison: OpenAI Realtime conversation.

Same `LocalAudioTransport` shape as Demo 1, but the LLM tier is OpenAI's
Realtime API (`gpt-realtime`) instead of the local llama-cpp stack. The
audience-facing comparison is "launch Demo 1 (local) → Esc → launch this →
hear the latency tax." Side-by-side simultaneous comparison was considered
and dropped: forking a single mic into two parallel pipelines is a noisy mess
on stage; sequential A/B is cleaner.

OpenAI Realtime handles STT + LLM + TTS itself, so this is just one Pipecat
service in the pipeline (vs. three for the local stack).
"""

from __future__ import annotations

import asyncio

from voice.menu import run_demo_with_ui, show_panel_until_escape
from voice.settings import Settings


SYSTEM_PROMPT = (
    "You are a concise, friendly voice assistant demoed live at a tech meetup "
    "about AI voice agents. Keep replies short — 1-2 sentences — and "
    "conversational."
)


async def run(settings: Settings) -> None:
    if not settings.has_openai:
        await show_panel_until_escape(
            title="API comparison · key missing",
            body_lines=[
                ("class:error", "OPENAI_API_KEY missing."),
                ("class:body", "Set it in .env and re-launch."),
                ("class:muted", "Get a key at https://platform.openai.com/api-keys"),
                ("class:muted", "Realtime API access required (not the standard chat API)."),
            ],
        )
        return

    try:
        from pipecat.services.openai.realtime.llm import (  # noqa: F401
            OpenAIRealtimeLLMService,
        )
        from pipecat.transports.local.audio import (  # noqa: F401
            LocalAudioTransport,
            LocalAudioTransportParams,
        )
    except ImportError as e:
        await show_panel_until_escape(
            title="API comparison · import failed",
            body_lines=[
                ("class:error", f"Pipecat OpenAI Realtime extras missing: {e}"),
                ("class:body", "Run `uv sync` to reinstall."),
            ],
        )
        return

    await run_demo_with_ui(
        title="API comparison · OpenAI Realtime (gpt-realtime)",
        demo_coro=lambda ui: _run_realtime(settings, ui),
        initial_lines=[
            ("class:body", "Connecting to OpenAI Realtime API..."),
        ],
    )


async def _run_realtime(settings: Settings, ui) -> None:  # type: ignore[no-untyped-def]
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import LLMMessagesAppendFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
    from pipecat.transports.local.audio import (
        LocalAudioTransport,
        LocalAudioTransportParams,
    )

    api_key = settings.OPENAI_API_KEY
    assert api_key  # has_openai gate above

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=24000,  # Realtime API native sample rate
            audio_out_sample_rate=24000,
        )
    )

    llm = OpenAIRealtimeLLMService(
        api_key=api_key,
        model="gpt-realtime",
    )

    # Realtime is end-to-end audio-in/audio-out, so the pipeline is short.
    pipeline = Pipeline(
        [
            transport.input(),
            llm,
            transport.output(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )

    ui.set_lines(
        [
            ("class:success", "Connected to OpenAI Realtime API · speak naturally"),
            ("class:muted", "Esc returns to the menu."),
            ("", ""),
            ("class:primary", "Stack:"),
            ("class:body", "  OpenAI gpt-realtime · cloud · WebSocket"),
            ("class:body", "  end-to-end audio-in / audio-out (no STT+LLM+TTS pipeline)"),
            ("", ""),
            (
                "class:muted",
                "A/B with Demo 1 (local) — listen for the latency difference.",
            ),
        ]
    )

    runner = PipelineRunner(handle_sigint=False)

    runner_task = asyncio.create_task(runner.run(task))
    stop_task = asyncio.create_task(ui.stop.wait())

    try:
        done, pending = await asyncio.wait(
            {runner_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        try:
            await task.cancel()
        except Exception:
            pass
        if not runner_task.done():
            runner_task.cancel()
            try:
                await runner_task
            except (asyncio.CancelledError, Exception):
                pass
