"""`voice doctor` — pre-flight check for the stage laptop.

Verifies audio devices, API key presence, and model cache state. Run this the
day before the talk; whatever it reports red is what you fix.
"""

from __future__ import annotations

from rich.table import Table

from voice.audio import default_input, default_output, list_devices
from voice.console import console
from voice.models import MODELS, cache_status
from voice.settings import Settings


def run_doctor() -> int:
    console.rule("[primary]voice doctor[/primary]")

    # ── Audio devices ─────────────────────────────────────────────
    console.print("\n[primary]Audio devices[/primary]")
    inp = default_input()
    out = default_output()
    inp_style = "success" if inp else "error"
    out_style = "success" if out else "error"
    console.print(
        f"  Default input:  [{inp_style}]{inp.name if inp else 'NONE'}[/{inp_style}]"
    )
    console.print(
        f"  Default output: [{out_style}]{out.name if out else 'NONE'}[/{out_style}]"
    )

    devices = list_devices()
    if devices:
        table = Table(
            title="All devices",
            show_lines=False,
            header_style="table.header",
            border_style="panel.border",
        )
        table.add_column("idx", justify="right", style="muted")
        table.add_column("name")
        table.add_column("in", justify="right")
        table.add_column("out", justify="right")
        for d in devices:
            table.add_row(
                str(d.index),
                d.name,
                str(d.max_input_channels),
                str(d.max_output_channels),
            )
        console.print(table)

    # ── API keys ──────────────────────────────────────────────────
    settings = Settings()
    console.print("\n[primary]API keys[/primary]")
    keys: list[tuple[str, bool, str]] = [
        ("OPENAI_API_KEY", settings.has_openai, "demo 3"),
        ("HUME_API_KEY + HUME_SECRET_KEY", settings.has_hume, "demo 4"),
        ("HF_TOKEN (optional)", bool(settings.HF_TOKEN), "model downloads"),
    ]
    for name, present, used_by in keys:
        marker = "[success]✓[/success]" if present else "[muted]–[/muted]"
        console.print(f"  {marker}  {name}  [muted]· {used_by}[/muted]")

    # ── Model cache ──────────────────────────────────────────────
    console.print("\n[primary]Model cache[/primary]")
    status = cache_status()
    for name, exists in status.items():
        marker = "[success]✓[/success]" if exists else "[warning]missing[/warning]"
        spec = MODELS[name]
        console.print(
            f"  {marker}  [accent]{name}[/accent]  "
            f"[muted]· {spec.description} (~{spec.approx_size_gb}GB)[/muted]"
        )

    console.print()
    return 0
