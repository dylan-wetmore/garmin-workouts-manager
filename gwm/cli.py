"""Command-line interface for the Garmin Workouts Manager.

    python -m gwm build   workouts/my.yaml        # preview JSON (no upload)
    python -m gwm push    workouts/my.yaml         # create/upload to Garmin
    python -m gwm list                             # list your Garmin workouts
    python -m gwm get     <workout_id>             # print one workout
    python -m gwm delete  <workout_id>             # delete a workout
    python -m gwm schedule <workout_id> 2026-08-10 # put it on your calendar
"""

from __future__ import annotations

import argparse
import json
import sys

from .builder import build_workout
from .schema import load_spec


def _load_dotenv():
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except ImportError:
        pass


def _client():
    from .client import GarminClient
    return GarminClient().login()


def cmd_build(args) -> int:
    spec = load_spec(args.file)
    payload = build_workout(spec)
    print(json.dumps(payload, indent=2))
    return 0


def _count_steps(steps):
    n = 0
    for s in steps:
        n += 1
        if s.get("type") == "RepeatGroupDTO":
            n += _count_steps(s["workoutSteps"])
    return n


def cmd_validate(args) -> int:
    spec = load_spec(args.file)
    payload = build_workout(spec)  # raises on any invalid exercise/target
    steps = payload["workoutSegments"][0]["workoutSteps"]
    named = sum(
        1 for s in _flatten(steps) if s.get("exerciseName")
    )
    print(
        f"✔ Valid: '{payload['workoutName']}' "
        f"[{payload['sportType']['sportTypeKey']}] — "
        f"{_count_steps(steps)} steps, {named} named exercise(s)"
    )
    return 0


def _flatten(steps):
    for s in steps:
        if s.get("type") == "RepeatGroupDTO":
            yield from _flatten(s["workoutSteps"])
        else:
            yield s


def cmd_push(args) -> int:
    spec = load_spec(args.file)
    payload = build_workout(spec)
    if getattr(args, "dry_run", False):
        named = sum(1 for s in _flatten(payload["workoutSegments"][0]["workoutSteps"]) if s.get("exerciseName"))
        print(f"✔ Dry run OK: '{payload['workoutName']}' — {named} named exercise(s). Not uploaded.")
        return 0
    client = _client()
    result = client.create_workout(payload)
    wid = result.get("workoutId")
    print(f"✔ Uploaded '{payload['workoutName']}' → workoutId {wid}")
    if args.date:
        client.schedule_workout(wid, args.date)
        print(f"✔ Scheduled for {args.date}")
    return 0


def cmd_update(args) -> int:
    spec = load_spec(args.file)
    payload = build_workout(spec)
    client = _client()
    client.update_workout(args.id, payload)
    print(f"✔ Updated workout {args.id} from '{payload['workoutName']}' (schedules kept)")
    return 0


def cmd_list(args) -> int:
    for w in _client().list_workouts(limit=args.limit):
        sport = (w.get("sportType") or {}).get("sportTypeKey", "?")
        print(f"{w.get('workoutId'):>12}  [{sport:<17}]  {w.get('workoutName')}")
    return 0


def cmd_get(args) -> int:
    print(json.dumps(_client().get_workout(args.id), indent=2))
    return 0


def cmd_delete(args) -> int:
    _client().delete_workout(args.id)
    print(f"✔ Deleted workout {args.id}")
    return 0


def cmd_schedule(args) -> int:
    _client().schedule_workout(args.id, args.date)
    print(f"✔ Scheduled workout {args.id} for {args.date}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gwm", description="Garmin Workouts Manager")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Preview the Garmin JSON without uploading")
    b.add_argument("file")
    b.set_defaults(func=cmd_build)

    pu = sub.add_parser("push", help="Upload a workout YAML to Garmin Connect")
    pu.add_argument("file")
    pu.add_argument("--date", help="Also schedule it (YYYY-MM-DD)")
    pu.add_argument("--dry-run", action="store_true", help="Build and validate only; do not upload")
    pu.set_defaults(func=cmd_push)

    va = sub.add_parser("validate", help="Build and validate a workout YAML without uploading")
    va.add_argument("file")
    va.set_defaults(func=cmd_validate)

    up = sub.add_parser("update", help="Replace an existing workout in place (keeps its schedules)")
    up.add_argument("id")
    up.add_argument("file")
    up.set_defaults(func=cmd_update)

    ls = sub.add_parser("list", help="List your Garmin workouts")
    ls.add_argument("--limit", type=int, default=50)
    ls.set_defaults(func=cmd_list)

    g = sub.add_parser("get", help="Print a single workout as JSON")
    g.add_argument("id")
    g.set_defaults(func=cmd_get)

    d = sub.add_parser("delete", help="Delete a workout")
    d.add_argument("id")
    d.set_defaults(func=cmd_delete)

    s = sub.add_parser("schedule", help="Schedule a workout on a date")
    s.add_argument("id")
    s.add_argument("date", help="YYYY-MM-DD")
    s.set_defaults(func=cmd_schedule)
    return p


def main(argv=None) -> int:
    _load_dotenv()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # keep tracebacks out of the user's way
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
