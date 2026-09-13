"""Garmin Connect workout-service constants.

These numeric IDs are Garmin's own (reverse-engineered from the workout
service — Garmin does not publish them). They are collected here so that if
Garmin ever changes one, there is a single place to fix it.
"""

# --- Sport types -----------------------------------------------------------
# sport key -> (sportTypeId, sportTypeKey)
SPORT_TYPES = {
    "running": (1, "running"),
    "cycling": (2, "cycling"),
    "swimming": (4, "swimming"),
    "strength": (5, "strength_training"),
    "cardio": (6, "cardio_training"),
}

# Friendly aliases the user (or Claude) might write in a YAML file.
SPORT_ALIASES = {
    "run": "running",
    "jog": "running",
    "treadmill": "running",
    "bike": "cycling",
    "cycle": "cycling",
    "ride": "cycling",
    "swim": "swimming",
    "pool": "swimming",
    "strength_training": "strength",
    "gym": "strength",
    "weights": "strength",
    "lifting": "strength",
    "cardio_training": "cardio",
    "hiit": "cardio",
    "elliptical": "cardio",
    "rowing": "cardio",
}

# --- Step types ------------------------------------------------------------
# step key -> (stepTypeId, stepTypeKey)
STEP_TYPES = {
    "warmup": (1, "warmup"),
    "cooldown": (2, "cooldown"),
    "interval": (3, "interval"),
    "recovery": (4, "recovery"),
    "rest": (5, "rest"),
    "repeat": (6, "repeat"),
}

# --- End conditions --------------------------------------------------------
# condition key -> (conditionTypeId, conditionTypeKey)
END_CONDITIONS = {
    "lap.button": (1, "lap.button"),
    "time": (2, "time"),
    "distance": (3, "distance"),
    "calories": (4, "calories"),
    "iterations": (7, "iterations"),  # used by repeat groups
    "reps": (10, "reps"),             # used by strength steps
}

# --- Target types ----------------------------------------------------------
# target key -> (workoutTargetTypeId, workoutTargetTypeKey)
TARGET_TYPES = {
    "no.target": (1, "no.target"),
    "power": (2, "power.zone"),
    "cadence": (3, "cadence.zone"),
    "hr": (4, "heart.rate.zone"),
    "speed": (5, "speed.zone"),
    "pace": (6, "pace.zone"),
}


def sport_type(key: str) -> dict:
    key = SPORT_ALIASES.get(key.lower(), key.lower())
    if key not in SPORT_TYPES:
        raise ValueError(
            f"Unknown sport '{key}'. Choose one of: "
            f"{', '.join(SPORT_TYPES)} (aliases like run/bike/gym also work)."
        )
    tid, tkey = SPORT_TYPES[key]
    return {"sportTypeId": tid, "sportTypeKey": tkey, "displayOrder": tid}


def step_type(key: str) -> dict:
    tid, tkey = STEP_TYPES[key]
    return {"stepTypeId": tid, "stepTypeKey": tkey, "displayOrder": tid}


def end_condition(key: str) -> dict:
    tid, tkey = END_CONDITIONS[key]
    return {"conditionTypeId": tid, "conditionTypeKey": tkey, "displayOrder": tid}


def target_type(key: str) -> dict:
    tid, tkey = TARGET_TYPES[key]
    return {"workoutTargetTypeId": tid, "workoutTargetTypeKey": tkey, "displayOrder": tid}
