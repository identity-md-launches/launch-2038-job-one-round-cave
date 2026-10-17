# Gatecheck

Gatecheck checks named intermediate handoff deadlines against a complete
offline schedule. Give each gate a set of tasks and a due time; the report
shows when that group finishes and its exact remaining slack. It first asks
Plancheck to validate the whole schedule, and withholds milestone results if
the schedule is incomplete or infeasible.

From the repository root, run the working example:

```sh
python3 -B line-1/tools/gatecheck/gatecheck.py --demo
```

The example reports a draft gate finishing exactly at minute 7 and a handoff
gate one minute ahead of its minute 10 due time.

Observed locally: `--demo` returned `valid: true`, with draft slack `0` and
handoff slack `1` minute.

For an actual plan, provide Workplan shaped task and plan files plus a gate file:

```json
{"gates":[{"id":"draft","tasks":["build","fixtures"],"due":7},{"id":"handoff","tasks":["check"],"due":10}]}
```

```sh
python3 -B line-1/tools/gatecheck/gatecheck.py --tasks tasks.json --plan plan.json --gates gates.json --workers 2 --budget 10
```

Gate IDs and task IDs must be unique within their lists; each gate must name
one or more existing tasks. A gate's finish is the latest finish among its
named tasks. It passes when that time is at or before `due`. Times use exact
decimal arithmetic and are printed as exact decimal strings so output never
rounds a boundary. A valid result establishes only that the supplied estimate
schedule meets the supplied gates; it does not predict real runtime or prove
optimality.

Exit 0 means the complete schedule and all gates pass, 2 means the schedule or
at least one gate fails, and 1 means the input is invalid. Plancheck is the
only runtime dependency and is read from its sibling tool folder. Both tools
are Python 3.9+ and use only the standard library.

## Checks

```sh
python3 -B line-1/tools/gatecheck/gatecheck.py --self-test
```

Eight checks cover an exact-on-time gate, positive slack, decimal arithmetic,
a late gate, withholding results for an invalid schedule, and malformed gate
definitions. These are local checks of supplied examples and boundaries.
