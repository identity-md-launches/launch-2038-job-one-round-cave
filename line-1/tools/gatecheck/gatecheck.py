#!/usr/bin/env python3
"""Check named handoff deadlines against a complete offline work schedule."""
import argparse
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "plancheck"))
import plancheck  # noqa: E402


def fields(obj, required):
    if not isinstance(obj, dict) or set(obj) != set(required):
        raise ValueError("expected exactly these fields: " + ", ".join(required))


def decimal_text(value):
    """Render an exact base-10 rational without rounding."""
    value = Fraction(value)
    numerator, denominator = value.numerator, value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ValueError("internal value is not a finite decimal")
    places = max(twos, fives)
    scaled = abs(numerator) * (10 ** places) // value.denominator
    digits = str(scaled).rjust(places + 1, "0")
    if places:
        whole, fractional = digits[:-places], digits[-places:]
        fractional = fractional.rstrip("0")
        rendered = whole + ("." + fractional if fractional else "")
    else:
        rendered = digits
    return ("-" if numerator < 0 else "") + rendered


def validate_gates(data, task_ids):
    fields(data, ("gates",))
    gates = data["gates"]
    if not isinstance(gates, list) or not 1 <= len(gates) <= 500:
        raise ValueError("gates must contain 1 to 500 entries")
    seen = set()
    checked = []
    for row in gates:
        fields(row, ("id", "tasks", "due"))
        name = row["id"]
        if not isinstance(name, str) or not name.strip() or len(name) > 100 or name in seen:
            raise ValueError("gate ids must be unique nonempty strings up to 100 characters")
        seen.add(name)
        tasks = row["tasks"]
        if (not isinstance(tasks, list) or not tasks or
                any(not isinstance(task, str) for task in tasks) or
                len(set(tasks)) != len(tasks)):
            raise ValueError("each gate needs a nonempty list of distinct task ids")
        unknown = sorted(set(tasks) - task_ids)
        if unknown:
            raise ValueError("unknown gate task id: " + unknown[0])
        due = plancheck.number(row["due"], "gate due")
        if due < 0:
            raise ValueError("gate due times must be nonnegative")
        checked.append({"id": name, "tasks": tasks, "due": due})
    return checked


def check(tasks_data, proposed, gates_data, workers, budget=None):
    """Validate the full schedule first, then report each named gate's slack."""
    tasks = plancheck.graph(tasks_data)
    gates = validate_gates(gates_data, set(tasks))
    schedule = plancheck.check(tasks_data, proposed, workers, budget)
    result = {
        "valid": False,
        "schedule_valid": schedule["valid"],
        "schedule_violations": schedule["violations"],
        "milestones": [],
        "arithmetic": "exact decimal minutes; no tolerance; times printed as exact strings",
    }
    if not schedule["valid"]:
        result["scope"] = "milestones are withheld until the complete schedule passes Plancheck"
        return result

    finish_by_task = {
        row["task"]: plancheck.number(row["finish"], "task finish")
        for row in proposed["schedule"]
    }
    late = []
    for gate in gates:
        finish = max(finish_by_task[task] for task in gate["tasks"])
        slack = gate["due"] - finish
        on_time = slack >= 0
        if not on_time:
            late.append(gate["id"])
        result["milestones"].append({
            "id": gate["id"],
            "tasks": gate["tasks"],
            "due_minutes": decimal_text(gate["due"]),
            "finish_minutes": decimal_text(finish),
            "slack_minutes": decimal_text(slack),
            "on_time": on_time,
        })
    result["valid"] = not late
    result["late_gates"] = sorted(late)
    result["scope"] = "named task groups only; estimates and worker availability are caller supplied"
    return result


def demo():
    tasks = {"tasks": [
        {"id": "read", "minutes": 2},
        {"id": "build", "minutes": 5, "after": ["read"]},
        {"id": "fixtures", "minutes": 3, "after": ["read"]},
        {"id": "check", "minutes": 2, "after": ["build", "fixtures"]},
    ]}
    plan = {"workers": 2, "finish": 9, "schedule": [
        {"task": "read", "worker": 1, "start": 0, "finish": 2},
        {"task": "build", "worker": 1, "start": 2, "finish": 7},
        {"task": "fixtures", "worker": 2, "start": 2, "finish": 5},
        {"task": "check", "worker": 1, "start": 7, "finish": 9},
    ]}
    gates = {"gates": [
        {"id": "draft", "tasks": ["build", "fixtures"], "due": 7},
        {"id": "handoff", "tasks": ["check"], "due": 10},
    ]}
    return check(tasks, plan, gates, 2, 10)


def self_test():
    good = demo()
    assert good["valid"] and good["milestones"][0]["slack_minutes"] == "0"
    assert good["milestones"][1]["slack_minutes"] == "1"

    data = {"tasks": [
        {"id": "a", "minutes": Decimal("0.1")},
        {"id": "b", "minutes": Decimal("0.2"), "after": ["a"]},
    ]}
    plan = {"workers": 1, "finish": Decimal("0.3"), "schedule": [
        {"task": "a", "worker": 1, "start": 0, "finish": Decimal("0.1")},
        {"task": "b", "worker": 1, "start": Decimal("0.1"), "finish": Decimal("0.3")},
    ]}
    exact = check(data, plan, {"gates": [
        {"id": "handoff", "tasks": ["b"], "due": Decimal("0.3")},
    ]}, 1)
    assert exact["valid"] and exact["milestones"][0]["slack_minutes"] == "0"

    late = check(data, plan, {"gates": [
        {"id": "handoff", "tasks": ["b"], "due": Decimal("0.29")},
    ]}, 1)
    assert not late["valid"] and late["late_gates"] == ["handoff"]
    assert late["milestones"][0]["slack_minutes"] == "-0.01"

    broken_plan = {"workers": 1, "finish": 0, "schedule": []}
    withheld = check(data, broken_plan, {"gates": [
        {"id": "handoff", "tasks": ["b"], "due": 1},
    ]}, 1)
    assert not withheld["schedule_valid"] and withheld["milestones"] == []

    for bad in (
        {"gates": [{"id": "g", "tasks": ["missing"], "due": 1}]},
        {"gates": [{"id": "g", "tasks": ["a", "a"], "due": 1}]},
        {"gates": [{"id": "g", "tasks": ["a"], "due": -1}]},
        {"gates": [{"id": "g", "tasks": ["a"], "due": 1},
                    {"id": "g", "tasks": ["b"], "due": 2}]},
    ):
        try:
            check(data, plan, bad, 1)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid gates were accepted: " + repr(bad))
    return {"tests": 8, "passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--tasks")
    parser.add_argument("--plan")
    parser.add_argument("--gates")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--budget")
    args = parser.parse_args()
    try:
        file_args = (args.tasks, args.plan, args.gates, args.workers, args.budget)
        if args.self_test:
            if args.demo or any(value is not None for value in file_args):
                raise ValueError("--self-test cannot be combined with other options")
            result, code = self_test(), 0
        elif args.demo:
            if any(value is not None for value in file_args):
                raise ValueError("--demo cannot be combined with file/check options")
            result, code = demo(), 0
            code = 0 if result["valid"] else 2
        else:
            if any(value is None for value in (args.tasks, args.plan, args.gates, args.workers)):
                raise ValueError("--tasks, --plan, --gates and --workers are required")
            budget = None if args.budget is None else Decimal(args.budget)
            result = check(plancheck.read_json(args.tasks), plancheck.read_json(args.plan),
                           plancheck.read_json(args.gates), args.workers, budget)
            code = 0 if result["valid"] else 2
        print(json.dumps(result, indent=2, allow_nan=False))
        return code
    except (ValueError, InvalidOperation, OSError, RecursionError, OverflowError) as exc:
        print("gatecheck: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
