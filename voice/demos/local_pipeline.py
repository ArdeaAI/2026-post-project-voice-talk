"""Demo 1 — Local pipeline (Pipecat + Moonshine v2 + Kokoro + llama-cpp).

Currently a stub. Real implementation drops in here once Pipecat services for
Moonshine and Kokoro are confirmed and the GGUF weights are cached. See
ai/cli_plan.md → "Demo 1" for the full spec.
"""

from __future__ import annotations

from voice.menu import show_panel_until_escape
from voice.settings import Settings


async def run(settings: Settings) -> None:  # noqa: ARG001
    await show_panel_until_escape(
        title="Local pipeline · stub",
        body_lines=[
            ("class:body", "Pipecat + Moonshine v2 + Kokoro + llama-cpp"),
            ("class:muted", "All Apache 2.0 / permissive · runs on this laptop"),
            ("", ""),
            ("class:warning", "Not wired up yet."),
            ("class:body", "See ai/cli_plan.md → 'Demo 1' for the spec."),
            ("", ""),
            ("class:muted", "Pre-flight before implementing:"),
            ("class:muted", "• useful-moonshine + kokoro-onnx + pipecat-ai install cleanly"),
            ("class:muted", "• Llama 3.2 3B Q4_K_M GGUF in ~/.cache/voice-cli/"),
            ("class:muted", "• Default mic + speakers verified via `voice doctor`"),
        ],
    )
