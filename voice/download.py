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
            # Reuse Pipecat's own auto-download path so we land files in
            # exactly the cache dir Pipecat's KokoroTTSService will read from
            # at demo launch — same files, same locations, full idempotency.
            from pipecat.services.kokoro.tts import (
                KOKORO_CACHE_DIR,
                _ensure_model_files,
            )
            from pathlib import Path

            t0 = time.monotonic()
            model_file = Path(KOKORO_CACHE_DIR) / "kokoro-v1.0.onnx"
            voices_file = Path(KOKORO_CACHE_DIR) / "voices-v1.0.bin"
            had_model = model_file.exists()
            had_voices = voices_file.exists()
            _ensure_model_files(model_file, voices_file)
            if had_model and had_voices:
                _ok(f"already cached at {KOKORO_CACHE_DIR}")
            else:
                _ok(f"downloaded to {KOKORO_CACHE_DIR} in {_human_seconds(t0)}")
        except Exception as exc:
            _fail(f"{exc}")
            failures += 1

    # ── Moshi MLX int8 ───────────────────────────────────────────
    if "moshi" in selected:
        _step("Moshi MLX int8 (~8GB) — Demo 2")
        try:
            from huggingface_hub import snapshot_download
            from huggingface_hub.errors import LocalEntryNotFoundError
            from huggingface_hub.utils import (
                disable_progress_bars,
                enable_progress_bars,
            )

            repo_id = "kyutai/moshiko-mlx-q8"

            # Cache-check first with the progress bar muted, so an idempotent
            # re-run doesn't render a 0.0s "Fetching 5 files" bar when there's
            # nothing to fetch. Only the real download (below) shows progress.
            disable_progress_bars()
            try:
                cached_path = snapshot_download(
                    repo_id=repo_id,
                    local_files_only=True,
                    token=settings.HF_TOKEN,
                )
                enable_progress_bars()
                _ok(f"already cached at {cached_path}")
            except (LocalEntryNotFoundError, OSError):
                enable_progress_bars()
                t0 = time.monotonic()
                cached_path = snapshot_download(
                    repo_id=repo_id,
                    token=settings.HF_TOKEN,
                )
                _ok(f"downloaded to {cached_path} in {_human_seconds(t0)}")
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
