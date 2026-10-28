"""Unit tests for the workout builder — no Garmin connection required."""

import math

from gwm import build_workout
from gwm.units import (
    parse_distance,
    parse_duration,
    parse_pace_target,
    parse_power_target,
    parse_weight,
)


def test_duration_parsing():
    assert parse_duration("10:00") == 600
    assert parse_duration("1:05:30") == 3930
    assert parse_duration("45min") == 2700
    assert parse_duration("30s") == 30
    assert parse_duration(90) == 90


def test_distance_parsing():
    assert parse_distance("400m") == 400
    assert parse_distance("5km") == 5000
    assert math.isclose(parse_distance("1mi"), 1609.344)


def test_weight_parsing():
    assert parse_weight("60kg") == 60
    assert math.isclose(parse_weight("100lb"), 45.359237)


def test_pace_target_mps_and_order():
    lo, hi = parse_pace_target("4:00-4:10", imperial=False)
    # 4:00/km == 4.1667 m/s (faster), 4:10/km == 4.0 m/s (slower)
    assert math.isclose(lo, 4.0, rel_tol=1e-3)
    assert math.isclose(hi, 1000 / 240, rel_tol=1e-3)
    assert lo < hi


def test_power_percent_needs_ftp():
    lo, hi = parse_power_target("88-94%", ftp=250)
    assert lo == 220 and hi == 235


def test_build_running_intervals():
    spec = {
        "name": "T",
        "sport": "run",
        "steps": [
            {"warmup": "10:00"},
            {"repeat": 3, "steps": [
                {"run": "3:00", "target": {"pace": "4:00-4:10"}},
                {"recover": "2:00"},
            ]},
            {"cooldown": "10:00"},
        ],
    }
    payload = build_workout(spec)
    assert payload["sportType"]["sportTypeKey"] == "running"
    steps = payload["workoutSegments"][0]["workoutSteps"]
    assert len(steps) == 3
    repeat = steps[1]
    assert repeat["type"] == "RepeatGroupDTO"
    assert repeat["numberOfIterations"] == 3
    assert len(repeat["workoutSteps"]) == 2
    interval = repeat["workoutSteps"][0]
    assert interval["endCondition"]["conditionTypeKey"] == "time"
    assert interval["endConditionValue"] == 180
    assert interval["targetType"]["workoutTargetTypeKey"] == "pace.zone"
    # children of a repeat share the group's childStepId
    assert interval["childStepId"] == repeat["childStepId"]


def test_build_strength_reps_and_weight():
    spec = {
        "name": "S",
        "sport": "strength",
        "steps": [
            {"exercise": "Squat", "reps": 10, "weight": "60kg"},
            {"rest": "1:30"},
        ],
    }
    payload = build_workout(spec)
    ex = payload["workoutSegments"][0]["workoutSteps"][0]
    assert ex["endCondition"]["conditionTypeKey"] == "reps"
    assert ex["endConditionValue"] == 10
    assert ex["weightValue"] == 60
    assert ex["description"] == "Squat"


def test_distance_end_condition():
    spec = {"name": "D", "sport": "run", "steps": [{"run": "400m"}]}
    step = build_workout(spec)["workoutSegments"][0]["workoutSteps"][0]
    assert step["endCondition"]["conditionTypeKey"] == "distance"
    assert step["endConditionValue"] == 400


def test_garmin_exercise_identifier_sets_fields():
    spec = {
        "name": "G", "sport": "strength",
        "steps": [
            {"exercise": "Back Squat",
             "garmin": {"category": "SQUAT", "name": "BARBELL_BACK_SQUAT"},
             "reps": 5, "weight": "40kg"},
        ],
    }
    step = build_workout(spec)["workoutSegments"][0]["workoutSteps"][0]
    assert step["category"] == "SQUAT"
    assert step["exerciseName"] == "BARBELL_BACK_SQUAT"
    assert step["endCondition"]["conditionTypeKey"] == "reps"
    assert step["weightValue"] == 40


def test_garmin_identifier_case_insensitive():
    spec = {"name": "G", "sport": "strength",
            "steps": [{"exercise": "Plank",
                       "garmin": {"category": "plank", "name": "plank"},
                       "time": "0:45"}]}
    step = build_workout(spec)["workoutSegments"][0]["workoutSteps"][0]
    assert step["category"] == "PLANK" and step["exerciseName"] == "PLANK"


def test_unknown_exercise_pair_raises():
    import pytest
    spec = {"name": "G", "sport": "strength",
            "steps": [{"exercise": "Nope",
                       "garmin": {"category": "SQUAT", "name": "NOT_A_REAL_LIFT"},
                       "reps": 5}]}
    with pytest.raises(ValueError):
        build_workout(spec)

    spec2 = {"name": "G", "sport": "strength",
             "steps": [{"exercise": "Nope",
                        "garmin": {"category": "FAKE", "name": "PLANK"},
                        "reps": 5}]}
    with pytest.raises(ValueError):
        build_workout(spec2)


def test_strength_without_garmin_is_unchanged():
    """No `garmin:` key -> category/exerciseName stay null (no regression)."""
    spec = {"name": "S", "sport": "strength",
            "steps": [{"exercise": "Goblet Squat", "reps": 10}]}
    step = build_workout(spec)["workoutSegments"][0]["workoutSteps"][0]
    assert step["category"] is None
    assert step["exerciseName"] is None
    assert step["description"] == "Goblet Squat"


def test_lap_button_end_condition():
    spec = {"name": "L", "sport": "run", "steps": [{"run": "lap"}]}
    step = build_workout(spec)["workoutSegments"][0]["workoutSteps"][0]
    assert step["endCondition"]["conditionTypeKey"] == "lap.button"
    assert step["endConditionValue"] is None
