from hud_window_state import HUDWindowState


def test_initial_state_is_full_hud_without_clickthrough():
    state = HUDWindowState(full_size=(620, 310), compact_size=(320, 110), position=(40, 50))

    assert state.mode == "full"
    assert state.clickthrough is False
    assert state.current_geometry() == "620x310+40+50"


def test_auto_start_switches_to_compact_clickthrough_mode():
    state = HUDWindowState(full_size=(620, 310), compact_size=(320, 110), position=(40, 50))

    state.enter_auto_run_mode()

    assert state.mode == "compact"
    assert state.clickthrough is True
    assert state.current_geometry() == "320x110+40+50"


def test_manual_start_keeps_full_mode():
    state = HUDWindowState(full_size=(620, 310), compact_size=(320, 110), position=(40, 50))

    state.enter_manual_run_mode()

    assert state.mode == "full"
    assert state.clickthrough is False
    assert state.current_geometry() == "620x310+40+50"


def test_restore_full_mode_after_run():
    state = HUDWindowState(full_size=(620, 310), compact_size=(320, 110), position=(40, 50))
    state.enter_auto_run_mode()

    state.restore_full_mode()

    assert state.mode == "full"
    assert state.clickthrough is False
    assert state.current_geometry() == "620x310+40+50"


def test_moving_window_preserves_position_across_modes():
    state = HUDWindowState(full_size=(620, 310), compact_size=(320, 110), position=(40, 50))

    state.update_position(180, 220)
    state.enter_auto_run_mode()

    assert state.current_geometry() == "320x110+180+220"
