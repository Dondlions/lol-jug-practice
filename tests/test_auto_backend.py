from auto_backend import AutoMonitorCoordinator


class FakeTimer:
    def __init__(self, available=True, reason=None):
        self.available = available
        self.reason = reason
        self.started = False
        self.stopped = False

    def probe(self, timeout_seconds=None):
        return self.available, self.reason

    def start_monitoring(self):
        self.started = True

    def stop_monitoring(self):
        self.stopped = True


def test_prefers_live_client_backend_when_available():
    live = FakeTimer(available=True)
    vision = FakeTimer()
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=vision)

    result = coordinator.start()

    assert result.backend == "riot_api"
    assert result.status_text == "[Riot API 监控中]"
    assert live.started is True
    assert vision.started is False


def test_falls_back_to_vision_when_live_client_unavailable():
    live = FakeTimer(available=False, reason="connection_failed")
    vision = FakeTimer()
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=vision)

    result = coordinator.start()

    assert result.backend == "vision"
    assert result.status_text == "[Riot API 不可用，已切换视觉识别]"
    assert result.fallback_reason == "connection_failed"
    assert live.started is False
    assert vision.started is True


def test_reports_unavailable_when_no_backend_can_start():
    live = FakeTimer(available=False, reason="ssl_error")
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=None)

    result = coordinator.start()

    assert result.backend == "unavailable"
    assert result.status_text == "[自动监控不可用]"
    assert result.fallback_reason == "ssl_error"


def test_stop_stops_active_backend():
    live = FakeTimer(available=True)
    vision = FakeTimer()
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=vision)

    coordinator.start()
    coordinator.stop()

    assert live.stopped is True
    assert vision.stopped is False
