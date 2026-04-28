"""Model registry — paths, HuggingFace IDs, lazy download.

Each demo declares the models it needs by name; this module owns the cache
location and the download mechanic. Real download logic lives behind
`ensure_model()` and uses `huggingface_hub` once a demo is actually wired in.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "voice-cli"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    huggingface_id: str
    description: str
    approx_size_gb: float
    notes: str = ""

    @property
    def cache_path(self) -> Path:
        return CACHE_DIR / self.name


# Verify HuggingFace IDs against PyPI / HF before pinning further. Marked here
# so `voice doctor` can flag missing weights without crashing.
MODELS: dict[str, ModelSpec] = {
    "moonshine_v2_medium": ModelSpec(
        name="moonshine_v2_medium",
        huggingface_id="UsefulSensors/moonshine",
        description="Moonshine v2 Medium Streaming STT (245M, ~107ms latency)",
        approx_size_gb=0.5,
        notes="Verify: moonshine-ai/moonshine repo for canonical HF id",
    ),
    "kokoro_82m": ModelSpec(
        name="kokoro_82m",
        huggingface_id="hexgrad/Kokoro-82M",
        description="Kokoro 82M TTS (Apache 2.0)",
        approx_size_gb=0.3,
    ),
    "llama_3_2_3b_instruct_q4": ModelSpec(
        name="llama_3_2_3b_instruct_q4",
        huggingface_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        description="Llama 3.2 3B Instruct (Q4_K_M GGUF)",
        approx_size_gb=2.0,
        notes="Specific file: Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    ),
    "moshi_mlx_q8": ModelSpec(
        name="moshi_mlx_q8",
        huggingface_id="kyutai/moshiko-mlx-q8",
        description="Moshi MLX int8 (~7B params quantized)",
        approx_size_gb=8.0,
    ),
}


def ensure_model(name: str) -> Path:
    """Return the cached path for a model, downloading if missing.

    NOT YET IMPLEMENTED — wires in `huggingface_hub.snapshot_download()` when
    the first real demo lands. Raises NotImplementedError so demo stubs that
    rely on it fail fast with a useful message.
    """
    spec = MODELS.get(name)
    if spec is None:
        raise KeyError(f"Unknown model: {name!r}. Known: {sorted(MODELS)}")
    if spec.cache_path.exists():
        return spec.cache_path
    raise NotImplementedError(
        f"Model {name!r} not yet downloaded and the auto-download path "
        "isn't wired up. Manually drop weights at "
        f"{spec.cache_path} or implement ensure_model()."
    )


def cache_status() -> dict[str, bool]:
    """Map model name to whether its cache directory exists locally."""
    return {name: spec.cache_path.exists() for name, spec in MODELS.items()}
