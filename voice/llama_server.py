"""Subprocess manager for llama-cpp-python's OpenAI-compatible HTTP server.

Demo 1's local LLM runs as a child process spawned with
asyncio.create_subprocess_exec (the safe variant — no shell, no string
interpolation). Pipecat's OpenAILLMService talks to it on localhost.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import httpx

from voice.process_registry import register, unregister


@asynccontextmanager
async def llama_server(
    model_path: Path,
    port: int = 18765,
    n_ctx: int = 4096,
    n_gpu_layers: int = -1,
    startup_timeout: float = 90.0,
) -> AsyncIterator[str]:
    """Start the llama-cpp HTTP server, yield base_url, kill on exit."""
    if not model_path.is_file():
        raise FileNotFoundError(f"GGUF not found at {model_path}")

    argv = [
        sys.executable,
        "-m",
        "llama_cpp.server",
        "--model",
        str(model_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--n_ctx",
        str(n_ctx),
        "--n_gpu_layers",
        str(n_gpu_layers),
    ]

    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,  # own process group so killpg() reaps the tree
    )
    register(proc)

    base_url = f"http://127.0.0.1:{port}/v1"

    try:
        deadline = asyncio.get_event_loop().time() + startup_timeout
        async with httpx.AsyncClient(timeout=2.0) as client:
            while True:
                if proc.returncode is not None:
                    raise RuntimeError(
                        f"llama-cpp server exited during startup "
                        f"(code {proc.returncode})"
                    )
                try:
                    response = await client.get(f"{base_url}/models")
                    if response.status_code == 200:
                        break
                except (httpx.ConnectError, httpx.ReadTimeout):
                    pass
                if asyncio.get_event_loop().time() > deadline:
                    raise TimeoutError(
                        f"llama-cpp server didn't respond within {startup_timeout}s"
                    )
                await asyncio.sleep(0.5)

        yield base_url

    finally:
        if proc.returncode is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
        unregister(proc)
