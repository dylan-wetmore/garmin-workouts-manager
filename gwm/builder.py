"""Turn a friendly workout definition (dict from YAML) into a Garmin payload.

The public entry point is :func:`build_workout`, which returns the JSON-ready
dict that Garmin's ``workout-service`` expects.
"""

from __future__ import annotations

import re

from . import constants as C
from . import units

# Step keyword -> Garmin step type. The keyword's *value* is the end condition
# (a duration, a distance, or "lap"); e.g. ``{warmup: 10:00}``.
STEP_KEYWORDS = {
    "warmup": "warmup",
    "warm-up": "warmup",
    "cooldown": "cooldown",
    "cool-down": "cooldown",
    "cool": "cooldown",
    "recover": "recovery",
    "recovery": "recovery",
    "rest": "rest",
    "interval": "interval",
    "work": "interval",
    "active": "interval",
    "hard": "interval",
    "run": "interval",
    "bike": "interval",
    "ride": "interval",
    "swim": "interval",
    "row": "interval",
    "step": "interval",
    "main": "interval",
    "go": "interval",
    "exercise": "interval",  # strength
}

TARGET_KEYS = ("power", "hr", "pace", "cadence", "speed")


class _Counter:
    def __init__(self):
        self.step_id = 0
        self.child_id = 0

    def next_step(self) -> int:
        self.step_id += 1
        return self.step_id

    def next_child(self) -> int:
        self.child_id += 1
        return self.child_id


def build_workout(spec: dict) -> dict:
    """Build the full Garmin workout payload from a workout ``spec`` dict."""
    if "name" not in spec:
        raise ValueError("Workout must have a 'name'.")
    if "sport" not in spec:
        raise ValueError("Workout must have a 'sport' (e.g. running, cycling, strength).")
    if not spec.get("steps"):
        raise ValueError("Workout must have at least one step under 'steps'.")

    sport = C.sport_type(spec["sport"])
    ctx = {
        "sport_key": sport["sportTypeKey"],
        "ftp": spec.get("ftp"),
        "imperial": str(spec.get("units", "metric")).lower().startswith("imp"),
    }
    counter = _Counter()
    steps = [_build_step(s, counter, ctx) for s in spec["steps"]]

    segment = {
        "segmentOrder": 1,
        "sportType": sport,
        "workoutSteps": steps,
    }
    if ctx["sport_key"] == "swimming" and spec.get("pool_length"):
        segment["poolLength"] = float(spec["pool_length"])
        segment["poolLengthUnit"] = {"unitKey": "meter"}

    payload = {
        "workoutName": spec["name"],
        "description": spec.get("description"),
        "sportType": sport,
        "workoutSegments": [segment],
    }
    if ctx["sport_key"] == "swimming" and spec.get("pool_length"):
        payload["poolLength"] = float(spec["pool_length"])
        payload["poolLengthUnit"] = {"unitKey": "meter"}
    return payload


# --------------------------------------------------------------------------
# Step building
# --------------------------------------------------------------------------

def _build_step(step, counter: _Counter, ctx: dict, child_id: int | None = None):
    if not isinstance(step, dict):
        raise ValueError(f"Each step must be a mapping, got: {step!r}")

    if "repeat" in step:
        return _build_repeat(step, counter, ctx)
    return _build_executable(step, counter, ctx, child_id)


def _build_repeat(step, counter: _Counter, ctx: dict):
    iterations = int(step["repeat"])
    inner = step.get("steps")
    if not inner:
        raise ValueError("A 'repeat' block needs a nested 'steps' list.")

    group_step_id = counter.next_step()
    group_child_id = counter.next_child()
    children = [_build_step(s, counter, ctx, child_id=group_child_id) for s in inner]

    return {
        "type": "RepeatGroupDTO",
        "stepId": group_step_id,
        "stepOrder": group_step_id,
        "stepType": C.step_type("repeat"),
        "childStepId": group_child_id,
        "numberOfIterations": iterations,
        "smartRepeat": False,
        "skipLastRestStep": False,
        "endCondition": C.end_condition("iterations"),
        "endConditionValue": float(iterations),
        "workoutSteps": children,
    }


def _find_keyword(step: dict):
    """Return (keyword, step_type_key) present in the step, or (None, None)."""
    for kw, st in STEP_KEYWORDS.items():
        if kw in step:
            return kw, st
    return None, None


def _build_executable(step, counter: _Counter, ctx: dict, child_id: int | None):
    keyword, step_type_key = _find_keyword(step)
    if keyword is None:
        raise ValueError(
            f"Step has no recognised type keyword {list(STEP_KEYWORDS)[:6]}...: {step!r}"
        )

    value = step[keyword]
    is_exercise = keyword == "exercise"
    dto = {
        "type": "ExecutableStepDTO",
        "stepId": counter.next_step(),
        "stepOrder": None,  # filled below to match stepId
        "stepType": C.step_type(step_type_key),
        "childStepId": child_id,
        "description": step.get("note") or step.get("description"),
    }
    dto["stepOrder"] = dto["stepId"]

    # --- end condition ---
    # For 'exercise' steps the keyword value is the *name*, so the end
    # condition comes from a sibling field (reps / time / distance).
    if "reps" in step:
        dto["endCondition"] = C.end_condition("reps")
        dto["endConditionValue"] = float(step["reps"])
    elif is_exercise and "time" in step:
        dto["endCondition"] = C.end_condition("time")
        dto["endConditionValue"] = round(units.parse_duration(step["time"]), 1)
    elif is_exercise and "distance" in step:
        dto["endCondition"] = C.end_condition("distance")
        dto["endConditionValue"] = round(units.parse_distance(step["distance"]), 2)
    elif is_exercise:
        dto["endCondition"] = C.end_condition("lap.button")
        dto["endConditionValue"] = None
    else:
        cond_key, cond_value = _classify_end_condition(value)
        dto["endCondition"] = C.end_condition(cond_key)
        dto["endConditionValue"] = cond_value

    # --- strength extras ---
    if is_exercise:
        if "garmin" in step:
            # Explicit Garmin exercise identifier: {category: ..., name: ...}.
            g = step["garmin"] or {}
            if "category" not in g or "name" not in g:
                raise ValueError(
                    f"garmin: needs both 'category' and 'name' (step: {value!r})"
                )
            cat, nm = C.validate_exercise(g["category"], g["name"])
            dto["category"] = cat
            dto["exerciseName"] = nm
            # exerciseName is the on-watch label; description stays as any note.
        else:
            # 'exercise: Squat' -> the name becomes the step label/description.
            if isinstance(value, str) and not step.get("note"):
                dto["description"] = value
            dto["category"] = None
            dto["exerciseName"] = None
        if "weight" in step:
            dto["weightValue"] = round(units.parse_weight(step["weight"]), 2)
            dto["weightUnit"] = {"unitKey": "kilogram"}

    # --- target ---
    dto.update(_build_target(step, ctx))
    return dto


def _classify_end_condition(value):
    """Decide whether ``value`` is time, distance, or a lap-button press."""
    if value is None:
        return "lap.button", None
    s = str(value).strip().lower()
    if s in ("lap", "press lap", "button", "manual", "open"):
        return "lap.button", None

    # Time if it looks clock-like or carries an explicit time unit.
    if ":" in s or s.endswith(("min", "mins", "sec", "secs", "h", "hr", "hrs")) or s.endswith("s"):
        return "time", round(units.parse_duration(value), 1)

    # Distance if it carries a distance unit.
    if s.endswith(("km", "mi", "mile", "miles", "yd", "yard", "yards", "m")):
        return "distance", round(units.parse_distance(value), 2)

    # Bare number -> seconds.
    return "time", round(units.parse_duration(value), 1)


def _build_target(step: dict, ctx: dict) -> dict:
    target = step.get("target")
    if target is None:
        # Allow shorthand: power/hr/pace/... directly on the step.
        target = {k: step[k] for k in TARGET_KEYS if k in step} or None
    if not target:
        return {
            "targetType": C.target_type("no.target"),
            "targetValueOne": None,
            "targetValueTwo": None,
            "targetValueUnit": None,
            "zoneNumber": None,
        }
    if len(target) != 1:
        raise ValueError(f"A step may have only one target, got: {list(target)}")

    (key, raw), = target.items()

    # Zone-based targets: e.g. {hr: z2} or {power: z3}. Uses the device's own
    # configured zones — no absolute bpm/watts needed.
    zmatch = re.fullmatch(r"z(?:one)?\s*([1-5])", str(raw).strip().lower()) if key in ("hr", "power") else None
    if zmatch:
        return {
            "targetType": C.target_type(key),
            "targetValueOne": None,
            "targetValueTwo": None,
            "targetValueUnit": None,
            "zoneNumber": int(zmatch.group(1)),
        }

    if key == "power":
        lo, hi = units.parse_power_target(raw, ctx.get("ftp"))
    elif key == "hr":
        lo, hi = units.parse_bpm_target(raw)
    elif key == "pace":
        lo, hi = units.parse_pace_target(raw, ctx["imperial"])
    elif key == "speed":
        lo, hi = units.parse_speed_target(raw)
    elif key == "cadence":
        lo, hi = units.parse_cadence_target(raw)
    else:
        raise ValueError(f"Unknown target '{key}'. Use one of {TARGET_KEYS}.")

    return {
        "targetType": C.target_type(key),
        "targetValueOne": float(lo),
        "targetValueTwo": float(hi),
        "targetValueUnit": None,
        "zoneNumber": None,
    }
