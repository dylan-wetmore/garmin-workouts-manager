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


def cmd_push(args) -> int:
    spec = load_spec(args.file)
    payload = build_workout(spec)
    client = _client()
    result = client.create_workout(payload)
    wid = result.get("workoutId")
    print(f"✔ Uploaded '{payload['workoutName']}' → workoutId {wid}")
    if args.date:
        client.schedule_workout(wid, args.date)
        print(f"✔ Scheduled for {args.date}")
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
    pu.set_defaults(func=cmd_push)

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
