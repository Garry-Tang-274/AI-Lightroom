from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QSettings, Qt

from app.ai.errors import AIRequestError
from app.ai.jarvisart.provider import JarvisArtProvider
from app.ai.jarvisart.runtime import LocalJarvisArtRuntime
from app.ai.jarvisart.service import JarvisArtServiceStatus
from app.ai.orchestrator import AIOrchestrator
from app.ai.progress import AIProgress
from app.ai.provider import AIProvider
from app.ai.provider_registry import provider_registry
from app.ai.schemas import EditingPlan
from app.ai.usage import AIUsageManager
from app.core.editor_state import EditorState
from app.ui.ai_panel import AIPanel
from app.ui.ai_worker import AIEditWorker
from app.utils.config import RuntimeSettings


def plan(**updates):
    return EditingPlan.model_validate({
        "summary": "Light edit", "reasoning_summary": "Preserve the subject.",
        "global_adjustments": [{"tool": "set_contrast", "value": 10}],
        "confidence": 0.9, **updates,
    })


def pixels():
    return np.full((40, 60, 3), 130, dtype=np.uint8)


class StubProvider(AIProvider):
    name = "Test provider"

    def __init__(self, on_call=lambda: None, reinspection=False):
        self.on_call = on_call
        self.reinspection = reinspection
        self.calls = 0
        self.requests = []

    def plan(self, request):
        self.on_call()
        self.calls += 1
        self.requests.append(request)
        return plan(needs_reinspection=self.reinspection)


def worker_fixture(monkeypatch, tmp_path, settings=None):
    store = QSettings(str(tmp_path / "usage.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("app.ui.ai_worker.QSettings", lambda *args: store)
    worker = AIEditWorker("edit", pixels(), EditorState(), [], settings or RuntimeSettings(), "synthetic-key", None)
    events, results, errors = [], [], []
    worker.signals.progress.connect(events.append)
    worker.signals.finished.connect(results.append)
    worker.signals.failed.connect(errors.append)
    return worker, events, results, errors, AIUsageManager(store)


def test_orchestrator_reports_observed_stages_without_claiming_transport():
    events = []
    provider = StubProvider()
    result = AIOrchestrator(provider, on_stage=lambda stage, message: events.append((stage, message))).process(
        "edit", pixels(), EditorState(), [],
    )
    assert [stage for stage, _ in events] == ["preparing_preview", "planning", "validating", "rendering"]
    assert not any("%" in message for _, message in events)
    assert result.has_changes and provider.calls == 1


def test_default_worker_has_one_observed_cloud_request(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path)
    provider = None

    def create(*args, **kwargs):
        nonlocal provider
        provider = StubProvider(kwargs["on_request_started"], reinspection=True)
        return provider

    monkeypatch.setattr(provider_registry, "create", create)
    worker.run()
    assert provider.calls == 1 and usage.status().today_count == 1
    assert len(results) == 1 and not errors
    waiting = next(event for event in events if event.stage == "waiting_cloud")
    assert waiting.request_number == 1 and waiting.request_sent and waiting.cloud
    assert all(not event.request_sent for event in events[:events.index(waiting)])
    assert events[-1].stage == "completed"


def test_explicit_reinspection_reports_second_request_and_counts_both(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path, RuntimeSettings(ai_reinspection=True))
    monkeypatch.setattr(provider_registry, "create", lambda *args, **kwargs: StubProvider(kwargs["on_request_started"], True))
    worker.run()
    assert not errors and len(results) == 1
    assert usage.status().today_count == 2
    assert [event.request_number for event in events if event.stage == "waiting_cloud"] == [1, 2]
    assert any(event.stage == "preparing_reinspection" for event in events)


@pytest.mark.parametrize("fail_after_cancel", [False, True])
def test_cancel_after_dispatch_discards_success_or_timeout_without_retry(monkeypatch, tmp_path, qtbot, fail_after_cancel):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path, RuntimeSettings(ai_reinspection=True))
    calls = []

    def create(*args, **kwargs):
        def call():
            kwargs["on_request_started"]()
            calls.append(True)
            worker.cancel()
            worker.cancel()
            if fail_after_cancel:
                raise TimeoutError("request timed out")
        return StubProvider(call, True)

    monkeypatch.setattr(provider_registry, "create", create)
    worker.run()
    assert calls == [True] and not results and len(errors) == 1
    assert errors[0].category == "已取消本地等待" and errors[0].request_sent
    assert "云端" in errors[0].message
    assert usage.status().today_count == 1
    assert usage.recent_events()[0]["result"] == "已取消本地等待"
    assert worker.is_cancelled and worker.state.is_pristine()
    assert sum(event.stage == "cancelling" for event in events) == 1
    assert events[-1].stage == "cancelled"
    assert not any(event.stage in {"validating", "rendering", "completed", "preparing_reinspection"} for event in events)


def test_cancel_before_dispatch_does_not_count_or_create_provider(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_registry, "create", lambda *args, **kwargs: pytest.fail("Must not create provider"))
    worker.cancel()
    worker.run()
    assert not results and not errors[0].request_sent
    assert "未发送推理请求" in errors[0].message
    assert usage.status().today_count == 0 and not usage.recent_events()


def test_budget_rejection_never_reports_cloud_wait(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path)
    usage.store.setValue("ai/budget_mode", "disabled")
    monkeypatch.setattr(provider_registry, "create", lambda *args, **kwargs: StubProvider(kwargs["on_request_started"]))
    worker.run()
    assert not results and errors[0].category == "本地 AI 费用保护"
    assert not any(event.request_sent for event in events)
    assert not any(event.stage == "waiting_cloud" for event in events)
    assert usage.status().today_count == 0


def test_mock_never_claims_a_local_or_cloud_inference_was_sent(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path, RuntimeSettings(provider="mock"))
    worker.run()
    assert not errors and len(results) == 1
    assert all(not event.request_sent for event in events)
    assert not any(event.stage in {"waiting_local", "waiting_cloud"} for event in events)
    assert usage.status().today_count == 0


def local_manager(start=None):
    return SimpleNamespace(endpoint="http://127.0.0.1:8765",
                           status=lambda: JarvisArtServiceStatus("Offline", "offline"),
                           start=start or (lambda: JarvisArtServiceStatus("Ready", "ready")))


def test_local_start_cancellation_prevents_post_and_does_not_stop_shared_service(monkeypatch):
    cancelled, stages, sent = [], [], []

    def start():
        cancelled.append(True)
        return JarvisArtServiceStatus("Ready", "ready")

    def check():
        if cancelled:
            raise AIRequestError("已取消本地等待", "cancelled")

    runtime = LocalJarvisArtRuntime(manager=local_manager(start),
                                  on_stage=lambda *args: stages.append(args),
                                  on_request_started=lambda: sent.append(True), check_cancelled=check)
    monkeypatch.setattr("app.ai.jarvisart.runtime.urlopen", lambda *args, **kwargs: pytest.fail("Must not POST"))
    with pytest.raises(AIRequestError, match="cancelled"):
        runtime.infer(b"jpeg", "edit", EditorState())
    assert not sent
    assert stages[0][0] == "starting_local_model" and "尚未发送" in stages[0][1]


def test_local_request_hook_is_at_post_boundary_and_temp_preview_is_removed(monkeypatch):
    sent, paths, stages = [], [], []
    runtime = LocalJarvisArtRuntime(manager=local_manager(),
                                  on_stage=lambda *args: stages.append(args),
                                  on_request_started=lambda: sent.append(True))

    def post(request, **kwargs):
        assert sent == [True] and kwargs["timeout"] == 300.0
        data = json.loads(request.data)
        paths.append(Path(data["photo_path"]))
        assert paths[0].read_bytes() == b"preview-only"
        return BytesIO(b"return {Exposure2012=-0.25}")

    monkeypatch.setattr("app.ai.jarvisart.runtime.urlopen", post)
    result = runtime.infer(b"preview-only", "edit", EditorState())
    assert result.global_adjustments[0].value == -0.25
    assert not paths[0].exists() and len(sent) == 1
    assert stages[0][0] == "starting_local_model"


def test_local_worker_tracks_actual_request_without_cloud_budget(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path, RuntimeSettings(provider="jarvisart_local"))
    runtime = LocalJarvisArtRuntime(manager=local_manager())
    monkeypatch.setattr("app.ai.jarvisart.runtime.urlopen", lambda *args, **kwargs: BytesIO(b"return {Exposure2012=-0.25}"))
    monkeypatch.setattr(provider_registry, "create", lambda config, key, **kwargs: JarvisArtProvider(config, runtime=runtime, **kwargs))
    worker.run()
    assert not errors and len(results) == 1
    waiting = next(event for event in events if event.stage == "waiting_local")
    assert waiting.request_sent and not waiting.cloud and waiting.request_number == 1
    assert results[0].provider_name == "JarvisArt Local GGUF · Ready"
    assert usage.status().today_count == 0 and not usage.recent_events()


def test_analysis_uses_configured_preview_copy_not_original(monkeypatch, tmp_path, qtbot):
    worker, events, results, errors, usage = worker_fixture(monkeypatch, tmp_path, RuntimeSettings(preview_size=640))
    original = np.full((1000, 2000, 3), 117, dtype=np.uint8)
    worker.source_pixels = original
    provider = StubProvider()
    monkeypatch.setattr(provider_registry, "create", lambda *args, **kwargs: provider)
    worker.run()
    sent_image = Image.open(BytesIO(provider.requests[0].preview_jpeg))
    assert sent_image.size == (640, 320)
    assert np.all(original == 117) and original.shape == (1000, 2000, 3)
    assert not errors and len(results) == 1


def test_panel_uses_monotonic_elapsed_time_and_freezes_on_finish(monkeypatch, qtbot):
    clock = [100.0]
    monkeypatch.setattr("app.ui.ai_panel.monotonic", lambda: clock[0])
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_ready(True)
    panel.set_busy(True)
    assert panel.elapsed_label.text() == "已等待 00:00"
    clock[0] = 338.2
    panel._update_elapsed()
    assert panel.elapsed_label.text() == "已等待 03:58"
    panel.set_busy(True)  # idempotent; repeated UI refresh must not reset time
    assert panel.elapsed_label.text() == "已等待 03:58"
    panel.set_busy(False)
    clock[0] = 500
    panel._update_elapsed()
    assert panel.elapsed_label.text() == "本次用时 03:58" and not panel._elapsed_timer.isActive()
    panel.set_busy(True)
    assert panel.elapsed_label.text() == "已等待 00:00"


def test_panel_cancel_is_single_shot_and_ignores_queued_older_progress(qtbot):
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_busy(True)
    calls = []
    panel.cancel_requested.connect(lambda: calls.append(True))
    panel.cancel_button.click()
    panel.cancel_button.click()
    assert calls == [True] and not panel.cancel_button.isEnabled()
    panel.set_progress(AIProgress("rendering", "should not overwrite cancel"))
    assert "已请求取消" in panel.progress_label.text()
    panel.set_progress(AIProgress("cancelling", "云端请求已发出，仍可能计费。", 1, True, True))
    assert "仍可能计费" in panel.progress_label.text()


def test_panel_retry_needs_available_ready_and_idle(qtbot):
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_retry_available(True)
    assert not panel.retry_button.isEnabled()
    panel.set_ready(True)
    assert panel.retry_button.isEnabled()
    panel.set_busy(True)
    assert not panel.retry_button.isEnabled()
    panel.set_busy(False)
    assert panel.retry_button.isEnabled()
    panel.set_retry_available(False)
    panel.set_busy(True)
    panel.set_busy(False)
    assert not panel.retry_button.isEnabled()


def test_panel_session_clear_removes_prompt_progress_and_retry(qtbot):
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_ready(True)
    panel.input.setPlainText("Only edit this photo")
    panel.add_assistant_message("prior photo")
    panel.set_retry_available(True)
    panel.set_busy(True)
    panel.clear_session()
    assert not panel.input.toPlainText() and not panel.transcript.toPlainText()
    assert not panel.progress_label.text() and panel.progress_label.isHidden()
    assert panel.elapsed_label.isHidden() and not panel._elapsed_timer.isActive()
    assert not panel.retry_button.isEnabled() and not panel.send_button.isEnabled()


def test_panel_multiline_submit_does_not_repeat_while_busy(qtbot):
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_ready(True)
    prompts = []
    panel.prompt_submitted.connect(lambda value: (prompts.append(value), panel.set_busy(True)))
    panel.input.setPlainText("保留主体")
    qtbot.keyClick(panel.input, Qt.Key.Key_End)
    qtbot.keyClick(panel.input, Qt.Key.Key_Return)
    assert not prompts and panel.input.document().blockCount() == 2
    qtbot.keyClick(panel.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    qtbot.keyClick(panel.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    panel.send_button.click()
    assert prompts == ["保留主体"]
