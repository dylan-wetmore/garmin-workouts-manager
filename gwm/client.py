"""Thin wrapper around Garmin Connect's workout API.

Authentication and transport are delegated to the ``garminconnect`` library,
which handles Garmin's native mobile SSO flow, MFA, and token caching. We just
hand it the workout payload our builder produced.
"""

from __future__ import annotations

import os

TOKEN_STORE = os.path.expanduser(os.getenv("GARMINTOKENS", "~/.garminconnect"))


class GarminError(RuntimeError):
    pass


def _import_garmin():
    try:
        from garminconnect import Garmin  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise GarminError(
            "The 'garminconnect' package is not installed. Run:\n"
            "    pip install garminconnect   (or)   uv sync"
        ) from e
    return Garmin


class GarminClient:
    """Authenticated Garmin Connect client scoped to workouts."""

    def __init__(self, email: str | None = None, password: str | None = None):
        self.email = email or os.getenv("GARMIN_EMAIL") or os.getenv("GARMIN_USERNAME")
        self.password = password or os.getenv("GARMIN_PASSWORD")
        self.api = None

    def login(self):
        Garmin = _import_garmin()
        # A cached token session means no password (or MFA) is needed again.
        try:
            api = Garmin()
            api.login(TOKEN_STORE)
            self.api = api
            return self
        except Exception:
            pass  # no valid cached session — do a fresh credential login

        if not self.email or not self.password:
            raise GarminError(
                "No cached Garmin session and no credentials found. Set "
                "GARMIN_EMAIL and GARMIN_PASSWORD (e.g. in a .env file), then retry."
            )
        api = Garmin(
            email=self.email,
            password=self.password,
            prompt_mfa=lambda: input("Garmin MFA code: ").strip(),
        )
        api.login(TOKEN_STORE)  # persists tokens to TOKEN_STORE on success
        self.api = api
        return self

    def _require(self):
        if self.api is None:
            raise GarminError("Not logged in — call login() first.")
        return self.api

    # -- workout operations ------------------------------------------------
    def create_workout(self, payload: dict) -> dict:
        return self._require().upload_workout(payload) or {}

    def update_workout(self, workout_id, payload: dict) -> dict:
        """Replace an existing workout in place (keeps its id and schedules)."""
        return self._require().update_workout(workout_id, payload) or {}

    def list_workouts(self, limit: int = 50, start: int = 0) -> list[dict]:
        return self._require().get_workouts(start=start, limit=limit) or []

    def get_workout(self, workout_id) -> dict:
        return self._require().get_workout_by_id(workout_id) or {}

    def delete_workout(self, workout_id):
        return self._require().delete_workout(workout_id)

    def schedule_workout(self, workout_id, date: str) -> dict:
        return self._require().schedule_workout(workout_id, date) or {}
