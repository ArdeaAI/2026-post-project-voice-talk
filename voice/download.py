"""`voice download` — pre-warm all model caches.

Runs the auto-download path each demo would hit on first launch, but does
them all up-front so you don't pay for a 10GB download mid-talk. Idempotent;
re-running is a no-op once everything is cached.
"""

from __future__ import annotations

import sys
import time

from voice.console import console
from voice.models import ensure_llama_gguf, llama_gguf_present
from voice.settings import Settings


def _step(label: str) -> None:
    console.print(f"\n[primary]→ {label}[/primary]")


def _ok(detail: str) -> None:
    console.print(f"  [success]✓[/success] {detail}")


def _skip(detail: str) -> None:
    console.print(f"  [muted]–[/muted] {detail}")


def _fail(detail: str) -> None:
    console.print(f"  [error]✗[/error] {detail}")


def _human_seconds(start: float) -> str:
    delta = time.monotonic() - start
    if delta < 60:
        return f"{delta:.1f}s"
    return f"{delta / 60:.1f}m"


def run_download(targets: list[str] | None = None) -> int:
    """Download model weights for the requested demos.

    Args:
        targets: Subset of {"llama", "whisper", "kokoro", "moshi"}. None = all.
    """
    settings = Settings()
    selected = set(targets) if targets else {"llama", "whisper", "kokoro", "moshi"}

    console.rule("[primary]voice download[/primary]")
    console.print(
        "[muted]Pre-warms model caches so demos start fast on stage. "
        "Re-runs are idempotent.[/muted]"
    )

    overall_start = time.monotonic()
    failures = 0

    # ── Llama 3.2 3B Q4_K_M GGUF ────────────────────────────────
    if "llama" in selected:
        _step("Llama 3.2 3B Instruct Q4_K_M GGUF (~2GB) — Demo 1, Demo 3 fallback")
        if llama_gguf_present():
            _skip("already cached")
        else:
            t0 = time.monotonic()
            try:
                path = ensure_llama_gguf(settings.HF_TOKEN)
                _ok(f"downloaded to {path} in {_human_seconds(t0)}")
            except Exception as exc:
                _fail(f"{exc}")
                failures += 1

    # ── faster-whisper base.en ───────────────────────────────────
    if "whisper" in selected:
        _step("faster-whisper base.en (~140MB) — Demo 1 STT")
        try:
            from faster_whisper import WhisperModel
            t0 = time.monotonic()
            # device="auto" picks Metal on Apple silicon. Loading triggers a
            # download into ~/.cache/huggingface/hub if not present.
            WhisperModel("base.en", device="auto", compute_type="default")
            _ok(f"loaded (cached) in {_human_seconds(t0)}")
        except Exception as exc:
            _fail(f"{exc}")
            failures += 1

    # ── Kokoro 82M ───────────────────────────────────────────────
    if "kokoro" in selected:
        _step("Kokoro 82M TTS (~300MB) — Demo 1 TTS")
        try:
            # kokoro-onnx auto-downloads its model + voices on first init.
            from kokoro_onnx import Kokoro  # type: ignore
            t0 = time.monotonic()
            # Kokoro() with no args uses bundled defaults and downloads from HF.
            try:
                _kokoro = Kokoro.from_pretrained()  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                # Older kokoro_onnx API — instantiate directly
                _kokoro = Kokoro(model_path=None, voices_path=None)  # type: ignore
            _ok(f"loaded (cached) in {_human_seconds(t0)}")
        except Exception as exc:
            _fail(
                f"{exc} — Kokoro auto-download path varies by version. "
                "Will fall back to demo-launch download."
            )
            # Don't count this as a hard failure; Pipecat's KokoroTTSService
            # will trigger the download on first synth instead.

    # ── Moshi MLX int8 ───────────────────────────────────────────
    if "moshi" in selected:
        _step("Moshi MLX int8 (~8GB) — Demo 2")
        try:
            from huggingface_hub import snapshot_download
            t0 = time.monotonic()
            # moshi-mlx pulls from kyutai/moshiko-mlx-q8 on first launch.
            # Pre-fetching the snapshot is the cleanest pre-warm.
            path = snapshot_download(
                repo_id="kyutai/moshiko-mlx-q8",
                token=settings.HF_TOKEN,
            )
            _ok(f"snapshot at {path} in {_human_seconds(t0)}")
        except Exception as exc:
            _fail(f"{exc}")
            failures += 1

    console.print()
    console.rule(f"[muted]done in {_human_seconds(overall_start)}[/muted]")
    if failures:
        console.print(f"[error]{failures} target(s) failed.[/error] Check the messages above.")
        return 1
    console.print("[success]All requested model caches are warm.[/success]")
    return 0


def main_cli() -> int:
    """Entry called by `voice download [target...]`."""
    args = sys.argv[2:]  # strip "voice" + "download"
    valid = {"llama", "whisper", "kokoro", "moshi", "all"}
    if not args or "all" in args:
        return run_download(None)
    unknown = [a for a in args if a not in valid]
    if unknown:
        console.print(
            f"[error]Unknown target(s): {', '.join(unknown)}[/error]\n"
            f"[muted]Valid: {', '.join(sorted(valid))}[/muted]"
        )
        return 2
    return run_download(args)
