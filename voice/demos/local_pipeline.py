"""Demo 1 — Local pipeline (Pipecat + Whisper + llama-cpp + Kokoro).

Runs entirely on the laptop, no cloud calls. The original plan called for
Moonshine v2 specifically; Pipecat 1.1.0 doesn't ship a first-party Moonshine
service, so we use faster-whisper (base.en) which has a Pipecat service and
hits the same "local STT is fast" beat. Swap to a custom MoonshineSTTService
later if you want to claim the Moonshine number on stage.

The LLM runs as a child subprocess — llama-cpp-python's OpenAI-compatible
HTTP server — and Pipecat's `OpenAILLMService` talks to it on localhost. That
keeps the Llama 3.2 3B GGUF in-process while reusing all of Pipecat's
streaming/tooling support.

Pipeline shape:

    LocalAudioTransport (mic + Silero VAD)
      → WhisperSTTService           (faster-whisper base.en)
      → OpenAILLMService            (llama-cpp server, localhost)
      → KokoroTTSService            (kokoro-onnx, 82M)
      → LocalAudioTransport (speaker)
"""

from __future__ import annotations

import asyncio

from voice.llama_server import llama_server
from voice.menu import run_demo_with_ui, show_panel_until_escape
from voice.models import ensure_llama_gguf, llama_gguf_path, llama_gguf_present
from voice.settings import Settings


SYSTEM_PROMPT = (
    "You are a concise, friendly voice assistant demoed live at a tech meetup "
    "about AI voice agents. Keep replies short — 1-2 sentences — and "
    "conversational. Do not narrate actions; just speak the response."
)


async def run(settings: Settings) -> None:
    # Import-guard heavy deps so a partial install doesn't crash the whole CLI.
    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer  # noqa: F401
        from pipecat.pipeline.pipeline import Pipeline  # noqa: F401
        from pipecat.services.kokoro.tts import KokoroTTSService  # noqa: F401
        from pipecat.services.openai.llm import OpenAILLMService  # noqa: F401
        from pipecat.services.whisper.stt import WhisperSTTService  # noqa: F401
        from pipecat.transports.local.audio import (  # noqa: F401
            LocalAudioTransport,
            LocalAudioTransportParams,
        )
    except ImportError as e:
        await show_panel_until_escape(
            title="Local pipeline · import failed",
            body_lines=[
                ("class:error", f"Pipecat extras missing: {e}"),
                ("class:body", "Run `uv sync` to reinstall deps."),
            ],
        )
        return

    await run_demo_with_ui(
        title="Local pipeline · Whisper + llama-cpp + Kokoro",
        demo_coro=lambda ui: _run_local_pipeline(settings, ui),
        initial_lines=[
            ("class:body", "Starting local pipeline..."),
        ],
    )


async def _run_local_pipeline(settings: Settings, ui) -> None:  # type: ignore[no-untyped-def]
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import LLMMessagesAppendFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.services.kokoro.tts import KokoroTTSService
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.services.whisper.stt import WhisperSTTService
    from pipecat.transports.local.audio import (
        LocalAudioTransport,
        LocalAudioTransportParams,
    )

    # ── Step 1: ensure the Llama GGUF is on disk ─────────────────
    if not llama_gguf_present():
        ui.set_lines(
            [
                ("class:body", "Downloading Llama 3.2 3B Q4_K_M GGUF (~2GB)..."),
                ("class:muted", "One-time. Cached at ~/.cache/voice-cli/"),
            ]
        )
        try:
            await asyncio.to_thread(ensure_llama_gguf, settings.HF_TOKEN)
        except Exception as exc:
            ui.set_lines(
                [
                    ("class:error", f"GGUF download failed: {exc}"),
                    ("class:body", "Manually drop the file at:"),
                    ("class:muted", f"  {llama_gguf_path()}"),
                ]
            )
            await ui.stop.wait()
            return

    gguf = llama_gguf_path()
    ui.set_lines(
        [
            ("class:success", f"Llama GGUF ready ({gguf.stat().st_size / 1e9:.1f} GB)"),
            ("class:body", "Booting llama-cpp HTTP server..."),
        ]
    )

    # ── Step 2: spin up the llama-cpp HTTP server in a subprocess ─
    try:
        async with llama_server(model_path=gguf) as base_url:
            ui.set_lines(
                [
                    ("class:success", f"llama-cpp server up at {base_url}"),
                    ("class:body", "Loading Whisper + Kokoro..."),
                ]
            )
            await _run_pipecat(settings, ui, base_url)
    except FileNotFoundError as exc:
        ui.set_lines([("class:error", str(exc))])
        await ui.stop.wait()
    except Exception as exc:
        ui.set_lines(
            [
                ("class:error", f"llama-cpp server crashed: {exc}"),
                ("class:muted", "Check that ~/.cache/voice-cli has the GGUF and Metal is available."),
            ]
        )
        await ui.stop.wait()


async def _run_pipecat(settings: Settings, ui, base_url: str) -> None:  # type: ignore[no-untyped-def]
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.services.kokoro.tts import KokoroTTSService
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.services.whisper.stt import WhisperSTTService
    from pipecat.transports.local.audio import (
        LocalAudioTransport,
        LocalAudioTransportParams,
    )

    # ── Transport (mic in, speaker out, Silero VAD on the input)
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,  # Kokoro's native rate
        )
    )

    # ── Services
    stt = WhisperSTTService(model="base.en")  # faster-whisper auto-downloads
    llm = OpenAILLMService(
        api_key="local-llamacpp",  # llama-cpp ignores keys but Pipecat requires one
        model="local",
        base_url=base_url,
    )
    tts = KokoroTTSService()  # kokoro-onnx auto-downloads its weights too

    # ── Pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            llm,
            tts,
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
            ("class:success", "Pipeline ready · speak naturally"),
            ("class:muted", "Esc returns to the menu."),
            ("", ""),
            ("class:primary", "STT:"),
            ("class:body", "  faster-whisper · base.en · local"),
            ("class:primary", "LLM:"),
            ("class:body", f"  llama-cpp · Llama 3.2 3B Q4_K_M · {base_url}"),
            ("class:primary", "TTS:"),
            ("class:body", "  kokoro-onnx · 82M · local"),
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
        for t in (runner_task,):
            if not t.done():
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
