"""Parsing helpers for human-friendly durations, distances, pace and targets."""

from __future__ import annotations

import re

METERS_PER_MILE = 1609.344
METERS_PER_YARD = 0.9144


def parse_duration(value) -> float:
    """'10:00' / '1:05:00' / '90s' / '45min' / 300 -> seconds (float)."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(s|sec|secs|m|min|mins|h|hr|hrs)?", s)
    if m and ":" not in s:
        num = float(m.group(1))
        unit = m.group(2) or "s"
        if unit.startswith("h"):
            return num * 3600
        if unit.startswith("m"):
            return num * 60
        return num
    parts = s.split(":")
    if not all(p.replace(".", "", 1).isdigit() for p in parts):
        raise ValueError(f"Cannot parse duration: {value!r}")
    parts = [float(p) for p in parts]
    if len(parts) == 2:  # mm:ss
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:  # hh:mm:ss
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Cannot parse duration: {value!r}")


def parse_distance(value) -> float:
    """'400m' / '5km' / '1.5mi' / '800yd' / 400 -> meters (float)."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(km|m|mi|mile|miles|yd|yard|yards)?", s)
    if not m:
        raise ValueError(f"Cannot parse distance: {value!r}")
    num = float(m.group(1))
    unit = m.group(2) or "m"
    if unit == "km":
        return num * 1000
    if unit in ("mi", "mile", "miles"):
        return num * METERS_PER_MILE
    if unit in ("yd", "yard", "yards"):
        return num * METERS_PER_YARD
    return num


def _pace_to_mps(pace: str, imperial: bool) -> float:
    """'4:30' (min per km, or per mile if imperial) -> speed in m/s."""
    sec = parse_duration(pace)
    per_meters = METERS_PER_MILE if imperial else 1000.0
    return per_meters / sec


def parse_range(value):
    """Split 'a-b' into (a, b); a single value into (a, a)."""
    s = str(value).strip()
    # Support en-dash too, and negative numbers are not expected here.
    s = s.replace("–", "-").replace("to", "-")
    if "-" in s:
        lo, hi = (p.strip() for p in s.split("-", 1))
        return lo, hi
    return s, s


def parse_pace_target(value, imperial: bool):
    """'4:00-4:10' -> (low_speed_mps, high_speed_mps) with low <= high."""
    lo, hi = parse_range(value)
    a = _pace_to_mps(lo, imperial)
    b = _pace_to_mps(hi, imperial)
    return (min(a, b), max(a, b))


def parse_speed_target(value):
    """'10-12' km/h -> (low_mps, high_mps)."""
    lo, hi = parse_range(value)
    a = float(lo) / 3.6
    b = float(hi) / 3.6
    return (min(a, b), max(a, b))


def parse_power_target(value, ftp: int | None):
    """'200-240' watts, or '88-95%' of FTP, or single value -> (low, high) watts."""
    lo, hi = parse_range(value)
    is_pct = "%" in str(value)
    lo = float(str(lo).replace("%", "").strip())
    hi = float(str(hi).replace("%", "").strip())
    if is_pct:
        if not ftp:
            raise ValueError("Power target uses % but no 'ftp' set on the workout.")
        lo, hi = lo / 100 * ftp, hi / 100 * ftp
    lo, hi = min(lo, hi), max(lo, hi)
    if lo == hi:  # Garmin wants a band; widen a hair for single values.
        lo, hi = lo - 2, hi + 2
    return (round(lo), round(hi))


def parse_bpm_target(value):
    """'150-160' -> (low, high) bpm."""
    lo, hi = parse_range(value)
    a, b = int(float(lo)), int(float(hi))
    a, b = min(a, b), max(a, b)
    if a == b:
        a, b = a - 2, b + 2
    return (a, b)


def parse_cadence_target(value):
    """'85-95' -> (low, high) rpm/spm."""
    lo, hi = parse_range(value)
    a, b = int(float(lo)), int(float(hi))
    a, b = min(a, b), max(a, b)
    if a == b:
        a, b = a - 2, b + 2
    return (a, b)


def parse_weight(value) -> float:
    """'60kg' / '135lb' / 60 -> kilograms (Garmin stores weight in kg)."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(kg|lb|lbs|pound|pounds)?", s)
    if not m:
        raise ValueError(f"Cannot parse weight: {value!r}")
    num = float(m.group(1))
    unit = m.group(2) or "kg"
    if unit.startswith("lb") or unit.startswith("pound"):
        return num * 0.45359237
    return num
