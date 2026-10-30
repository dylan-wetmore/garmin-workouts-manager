"""Live round-trip test — requires Garmin credentials/token.

Pushes a pull-up strength workout, GETs it back, asserts the Garmin exercise
identifiers (category / exerciseName) survive, then deletes it. Skipped unless
GWM_LIVE=1 so the normal offline suite needs no network.

    GWM_LIVE=1 pytest tests/test_live_roundtrip.py
"""

import os

import pytest

from gwm import build_workout

pytestmark = pytest.mark.skipif(
    os.getenv("GWM_LIVE") != "1",
    reason="set GWM_LIVE=1 to run the live Garmin round-trip test",
)


def _named_pairs(workout: dict):
    def walk(steps):
        for s in steps:
            if s.get("type") == "RepeatGroupDTO":
                yield from walk(s["workoutSteps"])
            elif s.get("exerciseName"):
                yield (s["category"], s["exerciseName"])
    return list(walk(workout["workoutSegments"][0]["workoutSteps"]))


def test_pullup_identifier_survives_roundtrip():
    from gwm.client import GarminClient

    payload = build_workout({
        "name": "ZZ gwm round-trip test",
        "sport": "strength",
        "steps": [
            {"exercise": "Pull-Up",
             "garmin": {"category": "PULL_UP", "name": "PULL_UP"}, "reps": 3},
        ],
    })
    client = GarminClient().login()
    created = client.create_workout(payload)
    wid = created.get("workoutId")
    assert wid, "no workoutId returned"
    try:
        fetched = client.get_workout(wid)
        assert ("PULL_UP", "PULL_UP") in _named_pairs(fetched)
    finally:
        client.delete_workout(wid)
