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
