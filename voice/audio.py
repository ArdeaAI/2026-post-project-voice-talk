"""Sounddevice helpers for the demos.

Used directly by Moshi (which doesn't speak Pipecat) and by the audio probe in
`voice doctor`. Pipecat-based demos use Pipecat's own transport layer instead.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import sounddevice as sd


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float

    @property
    def is_input(self) -> bool:
        return self.max_input_channels > 0

    @property
    def is_output(self) -> bool:
        return self.max_output_channels > 0


def list_devices() -> Sequence[AudioDevice]:
    """Return all input/output devices visible to the host."""
    devices = []
    for index, raw in enumerate(sd.query_devices()):
        devices.append(
            AudioDevice(
                index=index,
                name=raw["name"],
                max_input_channels=raw["max_input_channels"],
                max_output_channels=raw["max_output_channels"],
                default_sample_rate=raw["default_samplerate"],
            )
        )
    return devices


def default_input() -> AudioDevice | None:
    idx = sd.default.device[0]
    if idx < 0:
        return None
    return list_devices()[idx]


def default_output() -> AudioDevice | None:
    idx = sd.default.device[1]
    if idx < 0:
        return None
    return list_devices()[idx]


async def play_beep(
    frequency_hz: float = 440.0,
    duration_seconds: float = 0.3,
    sample_rate: int = 44100,
    amplitude: float = 0.3,
) -> None:
    """Play a short sine-wave beep on the default output device.

    Used by `voice doctor` to confirm speakers are wired up before the talk.
    Runs the blocking sounddevice call on a worker thread so it doesn't stall
    the asyncio event loop.
    """
    sample_count = int(sample_rate * duration_seconds)
    timeline = np.linspace(0, duration_seconds, sample_count, endpoint=False)
    waveform = (amplitude * np.sin(2 * np.pi * frequency_hz * timeline)).astype(
        np.float32
    )

    def _play() -> None:
        sd.play(waveform, samplerate=sample_rate)
        sd.wait()

    await asyncio.to_thread(_play)
