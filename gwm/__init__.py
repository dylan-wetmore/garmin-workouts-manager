"""Garmin Workouts Manager — describe workouts, sync them to Garmin devices."""

from .builder import build_workout
from .schema import load_spec

__all__ = ["build_workout", "load_spec"]
__version__ = "0.1.0"
