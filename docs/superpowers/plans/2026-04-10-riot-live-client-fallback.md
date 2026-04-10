# Riot Live Client Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prefer Riot's local Live Client Data API for automatic timing and fall back to the existing vision-based flow when the API is unavailable.

**Architecture:** Add a focused `LiveClientTimer` backend for polling local game data, plus a small coordinator that chooses between the API backend and `VisionTimer`. Keep `main.py` as the UI integration layer and route backend state into the existing automatic start/end callbacks.

**Tech Stack:** Python 3.7+, Tkinter, threading, urllib/ssl, pytest/unittest.mock

---

### Task 1: Add tests for Riot API parsing and failure handling

**Files:**
- Create: `tests/test_live_client_timer.py`
- Test: `tests/test_live_client_timer.py`

- [ ] **Step 1: Write the failing tests**

```python
from live_client_timer import LiveClientTimer, LiveClientError


def test_parses_game_time_from_gamestats_payload():
    timer = LiveClientTimer(fetch_json=lambda path: {"gameTime": 55.2} if "gamestats" in path else {"level": 3})
    assert timer.read_state().game_time == 55.2


def test_parses_active_player_level_from_payload():
    timer = LiveClientTimer(fetch_json=lambda path: {"gameTime": 10.0} if "gamestats" in path else {"level": 4})
    assert timer.read_state().level == 4


def test_reports_connection_failure_reason():
    def fetch_json(_path):
        raise LiveClientError("connection_failed", "offline")

    timer = LiveClientTimer(fetch_json=fetch_json)
    available, reason = timer.probe(timeout_seconds=0)
    assert available is False
    assert reason == "connection_failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_live_client_timer.py -q`
Expected: FAIL because `live_client_timer.py` and its API do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass
class LiveClientState:
    game_time: float
    level: int


class LiveClientError(Exception):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


class LiveClientTimer:
    def __init__(self, fetch_json):
        self.fetch_json = fetch_json

    def read_state(self):
        gamestats = self.fetch_json("/liveclientdata/gamestats")
        active_player = self.fetch_json("/liveclientdata/activeplayer")
        return LiveClientState(
            game_time=float(gamestats["gameTime"]),
            level=int(active_player["level"]),
        )

    def probe(self, timeout_seconds=0):
        try:
            self.read_state()
            return True, None
        except LiveClientError as exc:
            return False, exc.reason
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_live_client_timer.py -q`
Expected: PASS

### Task 2: Add tests for backend preference and fallback coordination

**Files:**
- Create: `tests/test_auto_backend.py`
- Create: `auto_backend.py`
- Test: `tests/test_auto_backend.py`

- [ ] **Step 1: Write the failing tests**

```python
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
    coordinator = AutoMonitorCoordinator(live, vision)

    result = coordinator.start()

    assert result.backend == "riot_api"
    assert live.started is True
    assert vision.started is False


def test_falls_back_to_vision_when_live_client_unavailable():
    live = FakeTimer(available=False, reason="connection_failed")
    vision = FakeTimer()
    coordinator = AutoMonitorCoordinator(live, vision)

    result = coordinator.start()

    assert result.backend == "vision"
    assert result.fallback_reason == "connection_failed"
    assert vision.started is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_auto_backend.py -q`
Expected: FAIL because `auto_backend.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass
class AutoMonitorResult:
    backend: str
    fallback_reason: str = None


class AutoMonitorCoordinator:
    def __init__(self, live_client_timer, vision_timer):
        self.live_client_timer = live_client_timer
        self.vision_timer = vision_timer
        self.active_backend = None

    def start(self):
        available, reason = self.live_client_timer.probe()
        if available:
            self.live_client_timer.start_monitoring()
            self.active_backend = "riot_api"
            return AutoMonitorResult(backend="riot_api")

        self.vision_timer.start_monitoring()
        self.active_backend = "vision"
        return AutoMonitorResult(backend="vision", fallback_reason=reason)

    def stop(self):
        if self.active_backend == "riot_api":
            self.live_client_timer.stop_monitoring()
        elif self.active_backend == "vision":
            self.vision_timer.stop_monitoring()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_auto_backend.py -q`
Expected: PASS

### Task 3: Implement the full Live Client backend and integrate it into the UI

**Files:**
- Create: `live_client_timer.py`
- Modify: `auto_backend.py`
- Modify: `main.py`
- Modify: `vision_timer.py`

- [ ] **Step 1: Expand the failing tests for real behavior**

Add coverage for:

```python
def test_probe_returns_invalid_data_when_required_fields_missing():
    ...


def test_start_uses_vision_when_live_client_raises_ssl_reason():
    ...
```

- [ ] **Step 2: Run targeted tests to verify the new expectations fail**

Run: `python3 -m pytest tests/test_live_client_timer.py tests/test_auto_backend.py -q`
Expected: FAIL with missing validation/fallback behavior.

- [ ] **Step 3: Implement the production code**

Key implementation points:

```python
# live_client_timer.py
# - add LiveClientState dataclass
# - add LiveClientError normalization helpers
# - use urllib.request + ssl._create_unverified_context()
# - validate /gamestats.gameTime and /activeplayer.level
# - poll in a thread
# - trigger callbacks at >= 55 seconds and >= 4 level

# auto_backend.py
# - add result fields for backend label, status text, failure reason
# - support unavailable state when neither backend can start

# main.py
# - create live client timer and coordinator
# - replace direct vision-only toggle logic with coordinator start/stop
# - keep vision preview/calibration actions working
# - show backend-specific status text

# vision_timer.py
# - make repeated start/stop safe after a completed run
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_live_client_timer.py tests/test_auto_backend.py -q`
Expected: PASS

### Task 4: Update docs and verify the feature end to end

**Files:**
- Modify: `README.md`
- Modify: `requirements.txt`

- [ ] **Step 1: Update docs**

Document:

```text
Automatic monitoring now prefers Riot's local Live Client Data API and falls back to vision recognition when the API is unavailable.
```

- [ ] **Step 2: Run verification**

Run: `python3 -m pytest -q`
Expected: PASS

- [ ] **Step 3: Run a syntax-level smoke check**

Run: `python3 -m compileall main.py live_client_timer.py auto_backend.py vision_timer.py tests`
Expected: PASS
