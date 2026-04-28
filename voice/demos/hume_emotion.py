"""Demo 4 — Hume EVI 3 emotion modeling.

Currently a stub. Real implementation opens an EVI WebSocket, streams mic in
and speaker out, and renders a real-time prosody readout (top-3 detected
emotions) in a Rich panel. Needs HUME_API_KEY + HUME_SECRET_KEY. See
ai/cli_plan.md → "Demo 4".
"""

from __future__ import annotations

from voice.menu import show_panel_until_escape
from voice.settings import Settings


async def run(settings: Settings) -> None:
    if not settings.has_hume:
        body = [
            ("class:error", "HUME_API_KEY / HUME_SECRET_KEY missing."),
            ("class:body", "Set both in .env and re-launch."),
        ]
    else:
        body = [
            ("class:body", "Hume EVI 3 · Octave 2 voice"),
            ("class:muted", "Live mic → emotion vector + spoken response"),
            ("", ""),
            ("class:warning", "Not wired up yet."),
            ("class:body", "See ai/cli_plan.md → 'Demo 4' for the spec."),
            ("", ""),
            ("class:muted", "Pre-flight before implementing:"),
            ("class:muted", "• `hume` Python SDK installs cleanly"),
            ("class:muted", "• HUME_API_KEY + HUME_SECRET_KEY mint a JWT"),
            ("class:muted", "• Network egress to api.hume.ai:443"),
        ]
    await show_panel_until_escape(
        title="Hume EVI 3 · stub",
        body_lines=body,
    )
