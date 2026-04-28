"""Smoke tests for the CLI skeleton.

Doesn't exercise the real demo pipelines — just confirms the structural
contracts (modules import, run() coroutines exist, menu lists are well-formed)
so a bad import doesn't surface for the first time mid-talk.
"""

from __future__ import annotations

import asyncio

from voice import audio, console, doctor, main, menu, models, settings
from voice.demos import api_comparison, hume_emotion, local_pipeline, moshi_e2e


def test_settings_loads_without_env() -> None:
    s = settings.Settings()
    assert s.OPENAI_API_KEY is None or isinstance(s.OPENAI_API_KEY, str)
    assert s.has_openai is bool(s.OPENAI_API_KEY)
    assert s.has_hume is (bool(s.HUME_API_KEY) and bool(s.HUME_SECRET_KEY))


def test_demos_have_async_run() -> None:
    for module in (local_pipeline, moshi_e2e, api_comparison, hume_emotion):
        assert hasattr(module, "run"), f"{module.__name__} missing run()"
        assert asyncio.iscoroutinefunction(module.run), (
            f"{module.__name__}.run must be a coroutine"
        )


def test_menu_lists_four_demos() -> None:
    assert len(menu.DEMOS) == 4
    ids = {d.id for d in menu.DEMOS}
    assert ids == {"local_pipeline", "moshi_e2e", "api_comparison", "hume_emotion"}


def test_menu_runner_paths_resolve() -> None:
    for entry in menu.DEMOS:
        fn = menu.resolve_runner(entry.runner_path)
        assert callable(fn)
        assert asyncio.iscoroutinefunction(fn)


def test_models_registry_complete() -> None:
    expected = {
        "moonshine_v2_medium",
        "kokoro_82m",
        "llama_3_2_3b_instruct_q4",
        "moshi_mlx_q8",
    }
    assert set(models.MODELS) == expected
    for spec in models.MODELS.values():
        assert spec.cache_path == models.CACHE_DIR / spec.name


def test_console_singleton_has_gruvbox_theme() -> None:
    # Theme entries should at least cover the styles used by the menu render
    for required in ("info", "warning", "error", "success", "muted", "accent"):
        assert console.GRUVBOX_THEME.styles.get(required) is not None


def test_audio_device_listing_has_expected_shape() -> None:
    devices = audio.list_devices()
    # CI may have no audio devices — just assert the call returns a sequence
    assert hasattr(devices, "__iter__")


def test_doctor_main_callable() -> None:
    assert callable(doctor.run_doctor)


def test_main_module_exposes_main() -> None:
    assert callable(main.main)
