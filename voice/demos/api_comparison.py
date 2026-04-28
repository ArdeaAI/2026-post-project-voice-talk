"""Demo 3 — API comparison: OpenAI Realtime vs. local pipeline.

Currently a stub. Real implementation runs both stacks side-by-side in a Rich
Layout, with first-byte latency and total response time displayed under each
pane. Needs OPENAI_API_KEY. See ai/cli_plan.md → "Demo 3".
"""

from __future__ import annotations

from voice.menu import show_panel_until_escape
from voice.settings import Settings


async def run(settings: Settings) -> None:
    if not settings.has_openai:
        # Defensive — the menu greys this out, but if someone bypassed it...
        body = [
            ("class:error", "OPENAI_API_KEY missing."),
            ("class:body", "Set it in .env and re-launch."),
        ]
    else:
        body = [
            ("class:body", "OpenAI Realtime API  vs.  local pipeline"),
            ("class:muted", "Same prompt → both stacks → hear the latency tax"),
            ("", ""),
            ("class:warning", "Not wired up yet."),
            ("class:body", "See ai/cli_plan.md → 'Demo 3' for the spec."),
            ("", ""),
            ("class:muted", "Pre-flight before implementing:"),
            ("class:muted", "• Realtime API access on this OpenAI account"),
            ("class:muted", "• Local pipeline (Demo 1) working"),
            ("class:muted", "• Network egress to api.openai.com:443"),
        ]
    await show_panel_until_escape(
        title="API comparison · stub",
        body_lines=body,
    )
