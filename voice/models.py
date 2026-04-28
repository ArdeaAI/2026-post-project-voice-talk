"""Model registry — paths, HuggingFace IDs, lazy download helpers.

Most demo dependencies (faster-whisper, kokoro-onnx, moshi-mlx) handle their
own model downloads on first inference. The one model we manage manually is
the Llama GGUF for Demo 1's local LLM, since llama-cpp-python takes a path
to a GGUF file rather than a model name.
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
    managed: bool  # True = we download it, False = the library handles it
    file_pattern: str | None = None  # for single-file downloads (GGUF)
    notes: str = ""

    @property
    def cache_path(self) -> Path:
        return CACHE_DIR / self.name


MODELS: dict[str, ModelSpec] = {
    "llama_3_2_3b_instruct_q4": ModelSpec(
        name="llama_3_2_3b_instruct_q4",
        huggingface_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        description="Llama 3.2 3B Instruct (Q4_K_M GGUF)",
        approx_size_gb=2.0,
        managed=True,
        file_pattern="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        notes="Downloaded by Demo 1 / Demo 3 on first launch.",
    ),
    "whisper_base_en": ModelSpec(
        name="whisper_base_en",
        huggingface_id="Systran/faster-whisper-base.en",
        description="Faster-Whisper base.en (English STT, ~140MB)",
        approx_size_gb=0.14,
        managed=False,
        notes="Auto-downloaded by faster-whisper on first transcription.",
    ),
    "kokoro_82m": ModelSpec(
        name="kokoro_82m",
        huggingface_id="hexgrad/Kokoro-82M",
        description="Kokoro 82M TTS (Apache 2.0)",
        approx_size_gb=0.3,
        managed=False,
        notes="Auto-downloaded by kokoro-onnx on first synthesis.",
    ),
    "moshi_mlx_q8": ModelSpec(
        name="moshi_mlx_q8",
        huggingface_id="kyutai/moshiko-mlx-q8",
        description="Moshi MLX int8 (~7B params quantized)",
        approx_size_gb=8.0,
        managed=False,
        notes="Auto-downloaded by moshi-mlx on first launch.",
    ),
}


def llama_gguf_path() -> Path:
    """Return the local path the Llama GGUF should live at."""
    spec = MODELS["llama_3_2_3b_instruct_q4"]
    assert spec.file_pattern is not None
    return spec.cache_path / spec.file_pattern


def llama_gguf_present() -> bool:
    return llama_gguf_path().is_file()


def ensure_llama_gguf(hf_token: str | None = None) -> Path:
    """Download the Llama 3.2 3B Q4_K_M GGUF if not cached. Returns local path.

    Uses huggingface_hub.hf_hub_download for a single-file fetch (~2GB).
    """
    if llama_gguf_present():
        return llama_gguf_path()

    from huggingface_hub import hf_hub_download

    spec = MODELS["llama_3_2_3b_instruct_q4"]
    assert spec.file_pattern is not None
    spec.cache_path.mkdir(parents=True, exist_ok=True)

    downloaded = hf_hub_download(
        repo_id=spec.huggingface_id,
        filename=spec.file_pattern,
        cache_dir=str(spec.cache_path),
        token=hf_token,
        local_dir=str(spec.cache_path),
    )
    return Path(downloaded)


def cache_status() -> dict[str, bool]:
    """Map model name -> whether its expected weights are present locally.

    For library-managed models, presence is best-effort (we check the cache
    directory). For our own GGUF, we check the exact file.
    """
    status: dict[str, bool] = {}
    for name, spec in MODELS.items():
        if spec.file_pattern is not None:
            status[name] = (spec.cache_path / spec.file_pattern).is_file()
        else:
            # Library-managed; just report whether the cache directory exists
            status[name] = spec.cache_path.exists()
    return status
