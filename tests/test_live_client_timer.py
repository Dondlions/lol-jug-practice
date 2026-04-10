import pytest

from live_client_timer import LiveClientError, LiveClientTimer


def make_timer(responses):
    def fetch_json(path):
        response = responses[path]
        if isinstance(response, Exception):
            raise response
        return response

    return LiveClientTimer(fetch_json=fetch_json, check_interval=0.01)


def test_read_state_parses_game_time_and_level():
    timer = make_timer(
        {
            "/liveclientdata/gamestats": {"gameTime": 55.2},
            "/liveclientdata/activeplayer": {"level": 4},
        }
    )

    state = timer.read_state()

    assert state.game_time == pytest.approx(55.2)
    assert state.level == 4


def test_probe_reports_connection_failure_reason():
    timer = make_timer(
        {
            "/liveclientdata/gamestats": LiveClientError(
                "connection_failed", "client offline"
            ),
            "/liveclientdata/activeplayer": {"level": 1},
        }
    )

    available, reason = timer.probe(timeout_seconds=0)

    assert available is False
    assert reason == "connection_failed"


def test_probe_reports_invalid_data_when_required_fields_missing():
    timer = make_timer(
        {
            "/liveclientdata/gamestats": {"gameTime": None},
            "/liveclientdata/activeplayer": {},
        }
    )

    available, reason = timer.probe(timeout_seconds=0)

    assert available is False
    assert reason == "invalid_data"


def test_process_state_resets_after_game_time_rolls_back_for_next_game():
    starts = []
    ends = []
    timer = LiveClientTimer(
        start_callback=lambda: starts.append("start"),
        end_callback=lambda: ends.append("end"),
        fetch_json=lambda _path: {"gameTime": 0, "level": 1},
        check_interval=0.01,
    )

    timer.process_state(timer.read_state().__class__(game_time=55.2, level=3))
    timer.process_state(timer.read_state().__class__(game_time=70.0, level=4))
    timer.process_state(timer.read_state().__class__(game_time=3.0, level=1))
    timer.process_state(timer.read_state().__class__(game_time=55.5, level=3))

    assert starts == ["start", "start"]
    assert ends == ["end"]
