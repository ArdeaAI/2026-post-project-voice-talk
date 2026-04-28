"""Demo 2 — Kyutai Moshi end-to-end speech-native.

Currently a stub. Real implementation uses moshi-mlx with the int8 quantized
weights (~8GB). Targets full-duplex conversation directly via sounddevice (no
Pipecat). See ai/cli_plan.md → "Demo 2".
"""

from __future__ import annotations

from voice.menu import show_panel_until_escape
from voice.settings import Settings


async def run(settings: Settings) -> None:  # noqa: ARG001
    await show_panel_until_escape(
        title="Moshi (end-to-end) · stub",
        body_lines=[
            ("class:body", "Kyutai Moshi · ~7B params · ~14GB bf16 (or ~8GB int8)"),
            ("class:muted", "Speech-native · full duplex · no STT/LLM/TTS pipeline"),
            ("", ""),
            ("class:warning", "Not wired up yet."),
            ("class:body", "See ai/cli_plan.md → 'Demo 2' for the spec."),
            ("", ""),
            ("class:muted", "Pre-flight before implementing:"),
            ("class:muted", "• moshi-mlx installed, MLX backend works on this M-series"),
            ("class:muted", "• Weights cached at ~/.cache/voice-cli/moshi_mlx_q8"),
            ("class:muted", "• Bundled Moshi CLI tested standalone first (`python -m moshi_mlx.local`)"),
        ],
    )
