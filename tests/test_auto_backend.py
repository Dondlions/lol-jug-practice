from auto_backend import AutoMonitorCoordinator


class FakeTimer:
    def __init__(self, available=True, reason=None):
        self.available = available
        self.reason = reason
        self.started = False
        self.stopped = False
        self.probe_calls = 0

    def probe(self, timeout_seconds=None):
        self.probe_calls += 1
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

    assert result.backend == "dual"
    assert result.status_text == "[双通道监控中]"
    assert live.started is True
    assert vision.started is True


def test_falls_back_to_vision_when_live_client_unavailable():
    live = FakeTimer(available=False, reason="connection_failed")
    vision = FakeTimer()
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=vision)

    result = coordinator.start()

    assert result.backend == "dual"
    assert result.status_text == "[双通道监控中]"
    assert result.fallback_reason == "connection_failed"
    assert live.started is True
    assert vision.started is True


def test_keeps_live_client_monitoring_even_without_vision():
    live = FakeTimer(available=False, reason="ssl_error")
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=None)

    result = coordinator.start()

    assert result.backend == "riot_api"
    assert result.status_text == "[Riot API 监控中]"
    assert result.fallback_reason == "ssl_error"
    assert live.started is True


def test_stop_stops_active_backend():
    live = FakeTimer(available=True)
    vision = FakeTimer()
    coordinator = AutoMonitorCoordinator(live_client_timer=live, vision_timer=vision)

    coordinator.start()
    coordinator.stop()

    assert live.stopped is True
    assert vision.stopped is True
