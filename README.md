# Garmin Workouts Manager

**Describe a workout in plain English, get it on your Garmin watch.**

Write workouts as small, readable YAML files — or have an AI assistant (Claude,
ChatGPT, etc.) write them for you — then sync them straight to Garmin Connect,
where they push to your watch or bike computer like any other structured workout.

Unlike most Garmin workout scripts (which are cycling/FTP-only), this handles
**running, cycling, swimming, strength/gym, and cardio** in one consistent
format, with targets by pace, heart rate, power, cadence, or speed.

```yaml
name: "Threshold Intervals"
sport: running
steps:
  - warmup: 10:00
  - repeat: 6
    steps:
      - run: 3:00
        target: {pace: 4:00-4:10}   # min/km
      - recover: 2:00
  - cooldown: 10:00
```

```bash
gwm push workouts/threshold-intervals.yaml    # → appears in Garmin Connect
```

---

## Why this exists

Garmin Connect's workout builder is slow and click-heavy, and there's no simple
way to keep workouts as text you can version, diff, reuse, or generate. This tool
treats a workout as a plain-text file:

- **Human-readable** — a whole interval session is a few lines of YAML.
- **AI-friendly** — describe it in a sentence and let an LLM produce the file
  (see [Using it with Claude / ChatGPT](#using-it-with-claude--chatgpt)).
- **Multi-sport** — one schema for runs, rides, swims, gym sessions, and cardio.
- **Version-controllable** — keep your training in git, not locked in an app.

There is **no official public Garmin workout API**, so this talks to the same
private endpoints the Garmin Connect website uses, via the community
[`garminconnect`](https://github.com/cyberjunky/python-garminconnect) library
(native mobile sign-in, MFA, and token caching).

---

## How it works

```
  You (or an AI)          this tool                     Garmin
 ────────────────    ───────────────────────      ────────────────────
  describe a     →   workouts/*.yaml         →     Garmin Connect  →  your
  workout            (build → Garmin JSON)         (workout library)   watch
```

1. A workout is a YAML file in `workouts/`.
2. `gwm build` turns it into Garmin's workout JSON (offline; a dry run).
3. `gwm push` uploads it to your Garmin Connect account.
4. Garmin syncs it to your devices.

---

## Install

Requires **Python 3.10+**.

```bash
# 1. Clone
git clone https://github.com/dylan-wetmore/garmin-workouts-manager.git
cd garmin-workouts-manager

# 2. Create a virtual environment and install
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e .

# 3. Add your Garmin credentials
cp .env.example .env                 # then edit .env
```

`.env`:

```
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your-garmin-password
```

Your password is used **only for the first login**. After that a token is
cached in `~/.garminconnect` (valid ~1 year) and reused, so you won't be asked
again. Accounts with two-factor auth are prompted for a code on first login.

> **Your credentials never leave your machine.** `.env` and the token cache are
> gitignored. This project is not affiliated with or endorsed by Garmin.

---

## Usage

```bash
gwm build    workouts/my.yaml                 # preview the Garmin JSON (no upload)
gwm validate workouts/my.yaml                 # check it builds & exercises are valid
gwm push     workouts/my.yaml                 # upload to Garmin Connect
gwm push     workouts/my.yaml --dry-run       # build & validate only, no upload
gwm push     workouts/my.yaml --date 2026-08-10 # upload AND schedule on your calendar
gwm update   <workout_id> workouts/my.yaml    # replace in place (keeps its schedules)
gwm list                                       # list your Garmin workouts (with IDs)
gwm get      <workout_id>                      # print one workout as JSON
gwm delete   <workout_id>                      # delete a workout
gwm schedule <workout_id> 2026-08-10           # schedule an existing workout
```

(You can also run any command as `python -m gwm ...` without installing.)

Start with `build` to preview, then `push` when it looks right.

---

## Using it with Claude / ChatGPT

This is the fast way to create workouts: let an AI write the YAML.

1. Open [`AI_PROMPT.md`](AI_PROMPT.md) and copy the prompt block into Claude,
   ChatGPT, or any assistant.
2. Describe your workout in plain English, e.g.
   *"Full-body gym session: 3 rounds of 12 goblet squats at 24 kg, 15 push-ups,
   12 bent-over rows at 40 kg, 90 s rest between rounds."*
3. Save the YAML it returns into `workouts/`.
4. `gwm push workouts/<that-file>.yaml`.

The prompt teaches the assistant the exact schema, so the output drops straight
in. If a file ever fails to build, paste the error back to the assistant and ask
it to fix the YAML.

> Using **Claude Code** or a similar agent? Point it at this repo and just say
> *"create a workout: …"* — it can write the file and run `gwm push` for you.

---

## Workout schema

A file has a few top-level fields and a list of `steps`.

| Field | Required | Notes |
|---|---|---|
| `name` | ✅ | Title shown in Garmin. |
| `sport` | ✅ | `running` \| `cycling` \| `swimming` \| `strength` \| `cardio` (aliases: run, bike, swim, gym, weights, hiit, rowing…). |
| `description` | | Free text. |
| `units` | | `metric` (pace per km, default) or `imperial` (per mile). |
| `ftp` | | Cycling only — integer watts; enables power targets as % of FTP. |
| `pool_length` | | Swimming only — meters. |
| `steps` | ✅ | Ordered list (see below). |

### Steps

Each step's **keyword sets its type** and its **value says when it ends**:

| Keyword | Garmin step type |
|---|---|
| `warmup` | Warm up |
| `cooldown` (`cool`) | Cool down |
| `work` / `interval` / `run` / `bike` / `swim` / `row` / `go` / `main` | Active interval |
| `recover` / `recovery` | Recovery |
| `rest` | Rest |
| `exercise` | Strength exercise (see below) |

The **value** is one of:

- a **duration** — `10:00`, `1:05:00`, `45min`, `30s`
- a **distance** — `400m`, `5km`, `1.5mi`, `800yd`
- `lap` — ends on lap-button press

> Bare numbers with no unit are treated as **seconds**; always add a unit for distance.

### Repeats

```yaml
- repeat: 4
  steps:
    - work: 400m
      target: {pace: 3:45-3:55}
    - recover: 90s
```

Repeats can be nested.

### Targets

Add an optional `target:` to any active step — exactly one type:

| Target | Example | Units |
|---|---|---|
| `pace` | `{pace: 4:00-4:10}` | min/km (or /mi if `units: imperial`) |
| `hr` | `{hr: 150-160}` | bpm |
| `power` | `{power: 200-240}` or `{power: 88-95%}` | watts, or % of `ftp` |
| `cadence` | `{cadence: 85-95}` | rpm / spm |
| `speed` | `{speed: 10-12}` | km/h |

A single value (e.g. `{hr: 155}`) is turned into a small band automatically.

### Strength / gym

```yaml
sport: strength
steps:
  - repeat: 3
    steps:
      - exercise: "Goblet Squat — 12 reps"
        reps: 12
        weight: 24kg          # or 135lb
      - rest: 1:00
      - exercise: "Plank"
        time: 0:45            # timed hold instead of reps
```

Exercise names show as the step label on your watch. Put rep ranges and
"each side" in the name; set `reps:` to a single number. Weight stores in kg
(`lb` is converted).

#### Naming exercises for Garmin (avoids "Unknown")

By default a strength step is a generic labelled step, so completed sessions log
the exercise as **"Unknown"** in Garmin/Strava. Add an optional `garmin:` key to
tag a step with Garmin's own exercise so it's recorded by name:

```yaml
- exercise: "Back Squat"        # cosmetic label
  garmin: {category: SQUAT, name: BARBELL_BACK_SQUAT}
  reps: 5
  note: "Leg press if rack taken"   # cues still show alongside the name
```

Pairs are validated at build time against [`gwm/exercises.py`](gwm/exercises.py)
(1,800+ exercises auto-generated from the Garmin FIT SDK) — an unknown
category/name fails loudly instead of silently uploading an unnamed step. Run
`gwm validate <file>` to check. Regenerate the list when the SDK updates:

```bash
pip install garmin-fit-sdk
python scripts/generate_exercises.py
```

Omit `garmin:` and the step behaves exactly as before.

See [`workouts/examples/`](workouts/examples) for full running, cycling,
strength, and cardio files.

### Pull-up programme (50pullups.com 6-8 cycle)

`workouts/examples/pullups-day-1.yaml` … `pullups-day-6.yaml` implement the
[50pullups.com 6-8 cycle](https://www.50pullups.com/50-pullups-programme/6-8-pullups)
(five sets, min 120 s rest between every set). Garmin can't express "max reps",
so the final set is modelled as `reps:` = the stated minimum with "MAX (min N)"
in the label.

> **The cycle MUST start on a Friday.** The programme requires a two-day rest
> after Days 3 and 6. Scheduling Fri → Wed → Fri … gives a four-day gap across
> each weekend, which satisfies that rest. Starting on a Wednesday puts Days 3
> and 6 on a Friday with only a one-day gap to the next session, violating the
> required rest.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `429` warnings on login | Garmin rate-limits sign-in; the cached token still works. If a push truly fails, wait a few minutes. |
| `No cached session and no credentials` | Set `GARMIN_EMAIL` / `GARMIN_PASSWORD` in `.env`. |
| MFA prompt every time | Ensure `~/.garminconnect` is writable so the token can be cached. |
| Upload suddenly fails | Garmin changed a private endpoint — `pip install -U garminconnect`. Sport/step IDs live in [`gwm/constants.py`](gwm/constants.py) for quick fixes. |

---

## Development

```bash
pip install -e ".[dev]"
pytest                 # builder is fully tested offline — no Garmin needed
```

Project layout:

```
gwm/
  builder.py     YAML spec  → Garmin workout JSON
  constants.py   Garmin sport / step / target IDs (one place to patch)
  units.py       parse durations, distances, pace, power %, weights
  client.py      auth + upload / list / delete / schedule
  cli.py         the `gwm` commands
workouts/
  examples/      sample workouts for each sport
```

---

## Disclaimer

This is an unofficial tool that uses Garmin Connect's private web endpoints. It
can break if Garmin changes them, and using it is at your own risk. Not
affiliated with, endorsed by, or supported by Garmin. "Garmin" and "Garmin
Connect" are trademarks of Garmin Ltd.

## License

[MIT](LICENSE) © 2026 Dylan Wetmore
