# Riot Live Client Fallback Design

## Summary

This desktop timer should prefer Riot's local Live Client Data API for automatic run timing and fall back to the existing screen-vision flow when the local API is unavailable. The user-facing workflow stays the same: one automatic monitoring toggle, automatic start at `0:55`, and automatic completion at level `4`.

## Goals

- Prefer Riot's official local API over OCR when live game data is available.
- Preserve the current automatic workflow and UI layout.
- Fall back to vision monitoring without requiring extra user action.
- Make the active detection backend visible in the UI.
- Add automated tests for the new backend-selection logic.

## Non-Goals

- Reworking the Tkinter layout.
- Removing the existing vision-based implementation.
- Adding support for Riot's public developer APIs.
- Tracking camp spawn timers from Riot event streams in this change.

## Current State

`main.py` currently wires the automatic mode directly to `VisionTimer`. `vision_timer.py` performs screen capture, OCR-like time recognition, and level recognition in a polling loop. This works without network calls, but it is sensitive to resolution, UI scaling, OCR drift, and local calibration.

## Proposed Approach

### Detection Backends

Introduce a dedicated `LiveClientTimer` backend in a new module, likely `live_client_timer.py`.

Responsibilities:

- Poll Riot's local Live Client Data API over `https://127.0.0.1:2999`.
- Read current game time from `/liveclientdata/gamestats`.
- Read active player level from `/liveclientdata/activeplayer`.
- Trigger the same start and end callbacks used by `VisionTimer`.
- Report availability and failure reasons to the caller.

Keep `VisionTimer` as the fallback backend with its current callback-based contract.

### Backend Selection

Add a lightweight controller in `main.py` that manages automatic monitoring:

1. When the user enables automatic monitoring, attempt to start `LiveClientTimer`.
2. If the local API is reachable and returns valid in-game data, stay on `LiveClientTimer`.
3. If the API is unreachable, has SSL issues, returns invalid payloads, or cannot confirm game state within a short startup window, stop API monitoring and switch to `VisionTimer`.
4. If vision monitoring is also unavailable, show a clear error and leave auto-monitoring disabled.

This controller does not need to be a large abstraction layer. A focused helper or small coordinator class is enough for this project.

### Runtime Behavior

The automatic mode keeps the current user-facing behavior:

- Start condition: game time reaches `0:55`.
- End condition: active player level reaches `4` or higher.

Backend-specific behavior:

- `LiveClientTimer` uses parsed API data instead of OCR.
- `VisionTimer` remains unchanged except for any integration adjustments needed for clearer status reporting.

### UI Updates

Keep one checkbox/toggle for automatic monitoring. Update nearby status text so users can see the active backend and fallback outcome.

Examples:

- `[Riot API 监控中]`
- `[Riot API 不可用，已切换视觉识别]`
- `[视觉识别监控中]`
- `[自动监控不可用]`

The existing "visual recognition" wording may remain for now to avoid unnecessary UI churn, but the live status should make the actual backend explicit.

## Error Handling

`LiveClientTimer` should normalize failures into a small set of reasons so `main.py` can decide whether to fall back quietly or surface a user-visible message:

- Connection failure: client not running, no active game, or port `2999` not responding.
- SSL failure: local certificate verification problem.
- Invalid data: response is present but required fields such as `gameTime` or player `level` are missing.
- Startup timeout: API never yields usable in-game data within the startup grace period.

Expected handling:

- Any of the above should trigger automatic fallback to `VisionTimer`.
- Only show an explicit blocking error if both backends are unavailable.
- Debug/test actions should surface the concrete backend failure reason when useful.

## Testing Strategy

Add `pytest`-based tests around the new backend logic rather than around the Tk UI itself.

Test coverage should include:

- Parsing valid game time from the Riot local API response.
- Parsing active player level from the Riot local API response.
- Marking the API backend unavailable on request/SSL/data failures.
- Preferring the Riot API backend when it is healthy.
- Falling back to `VisionTimer` when the Riot API backend is unavailable.

The tests should focus on small units that do not require a running League client or a real display capture session.

## File Plan

Expected file changes:

- Add `live_client_timer.py` for Riot local API polling and parsing.
- Modify `main.py` to coordinate backend selection and status reporting.
- Possibly update `requirements.txt` if an HTTP dependency is needed.
- Add tests under `tests/` for the new backend and fallback controller logic.
- Update `README.md` to explain that automatic mode now prefers Riot's local API and falls back to vision.

## Design Notes

- Prefer the standard library for HTTP if practical to keep dependencies light; if that becomes awkward for local HTTPS handling, a minimal `requests`-based implementation is acceptable.
- Keep callback names and timer semantics aligned with `VisionTimer` so integration stays simple.
- Avoid over-engineering a generalized plugin system for backends. Two backends with a small shared contract are enough here.

## Success Criteria

- Automatic monitoring works without OCR when Riot's local Live Client API is available.
- Users do not need to manually choose between API mode and vision mode.
- Auto-monitoring still works when the local API cannot be used, provided vision mode is available.
- The UI clearly communicates which backend is active.
- New automated tests cover the API backend and fallback flow.
