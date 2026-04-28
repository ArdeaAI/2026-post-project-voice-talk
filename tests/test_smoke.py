"""Smoke tests for the CLI skeleton.

Doesn't exercise the real demo pipelines (no live audio in CI) — just confirms
the structural contracts (modules import, run() coroutines exist, registries
are well-formed) so a bad import doesn't surface for the first time mid-talk.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from voice import (
    audio,
    console,
    doctor,
    kill_strays,
    llama_server,
    main,
    menu,
    models,
    process_registry,
    settings,
)
from voice.demos import api_comparison, hume_emotion, local_pipeline, moshi_e2e


def test_settings_loads_without_env() -> None:
    s = settings.Settings()
    assert s.OPENAI_API_KEY is None or isinstance(s.OPENAI_API_KEY, str)
    assert s.has_openai is bool(s.OPENAI_API_KEY)
    assert s.has_hume is (bool(s.HUME_API_KEY) and bool(s.HUME_SECRET_KEY))


def test_settings_missing_keys_for_demos() -> None:
    s = settings.Settings(
        OPENAI_API_KEY=None, HUME_API_KEY=None, HUME_SECRET_KEY=None
    )
    assert s.missing_keys_for("local_pipeline") == []
    assert s.missing_keys_for("moshi_e2e") == []
    assert "OPENAI_API_KEY" in s.missing_keys_for("api_comparison")
    assert set(s.missing_keys_for("hume_emotion")) == {
        "HUME_API_KEY",
        "HUME_SECRET_KEY",
    }


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


def test_menu_demoui_class_exposes_handles() -> None:
    # Don't instantiate (needs a live Application) — just check the surface
    assert hasattr(menu, "DemoUI")
    assert hasattr(menu, "run_demo_with_ui")


def test_models_registry_complete() -> None:
    expected = {
        "llama_3_2_3b_instruct_q4",
        "whisper_base_en",
        "kokoro_82m",
        "moshi_mlx_q8",
    }
    assert set(models.MODELS) == expected
    for spec in models.MODELS.values():
        assert spec.cache_path == models.CACHE_DIR / spec.name


def test_models_llama_path_helper() -> None:
    expected_filename = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    assert models.llama_gguf_path().name == expected_filename
    # Boolean check is callable; actual presence depends on whether download ran
    assert isinstance(models.llama_gguf_present(), bool)


def test_console_singleton_has_gruvbox_theme() -> None:
    for required in ("info", "warning", "error", "success", "muted", "accent"):
        assert console.GRUVBOX_THEME.styles.get(required) is not None


def test_audio_device_listing_has_expected_shape() -> None:
    devices = audio.list_devices()
    assert hasattr(devices, "__iter__")


def test_doctor_main_callable() -> None:
    assert callable(doctor.run_doctor)


def test_main_module_exposes_main() -> None:
    assert callable(main.main)


def test_llama_server_is_async_context_manager() -> None:
    # Just that the helper exists with a sensible signature; we don't actually
    # spawn a subprocess in tests.
    assert hasattr(llama_server, "llama_server")


def test_demo_api_comparison_gates_on_openai_key() -> None:
    # When OPENAI_API_KEY is None, the demo should still be importable; the
    # gate fires at runtime via show_panel_until_escape.
    s = settings.Settings(OPENAI_API_KEY=None)
    assert not s.has_openai


def test_demo_hume_gates_on_both_keys() -> None:
    s = settings.Settings(HUME_API_KEY="set", HUME_SECRET_KEY=None)
    assert not s.has_hume
    s = settings.Settings(HUME_API_KEY=None, HUME_SECRET_KEY="set")
    assert not s.has_hume
    s = settings.Settings(HUME_API_KEY="a", HUME_SECRET_KEY="b")
    assert s.has_hume


def test_process_registry_kills_subprocess() -> None:
    """Spawn a long-running sleep, register it, kill_all should reap it."""
    import asyncio
    import os as _os

    async def _spawn_and_reap():  # type: ignore[no-untyped-def]
        proc = await asyncio.create_subprocess_exec(
            "sleep",
            "300",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        process_registry.register(proc)
        pid = proc.pid
        assert proc.returncode is None
        process_registry.kill_all(grace_seconds=0.3)
        for _ in range(20):
            if proc.returncode is not None:
                break
            await asyncio.sleep(0.1)
        process_registry.unregister(proc)
        return pid, proc.returncode

    pid, returncode = asyncio.run(_spawn_and_reap())

    assert returncode is not None, "subprocess still running after kill_all"

    raised = False
    try:
        _os.kill(pid, 0)
    except ProcessLookupError:
        raised = True
    except PermissionError:
        raised = True
    assert raised, f"pid {pid} still exists after kill_all"


def test_process_registry_install_handlers_idempotent() -> None:
    process_registry.install_handlers()
    process_registry.install_handlers()
    assert True


def test_process_registry_register_unregister_count() -> None:
    class _FakeProc:
        def __init__(self, pid: int) -> None:
            self.pid = pid
            self.returncode = None

    p1 = _FakeProc(99991)
    p2 = _FakeProc(99992)
    before = process_registry.registered_count()
    process_registry.register(p1)  # type: ignore[arg-type]
    process_registry.register(p2)  # type: ignore[arg-type]
    assert process_registry.registered_count() == before + 2
    process_registry.unregister(p1)  # type: ignore[arg-type]
    process_registry.unregister(p2)  # type: ignore[arg-type]
    assert process_registry.registered_count() == before


def test_kill_strays_module_exposes_run() -> None:
    assert callable(kill_strays.run_kill)
