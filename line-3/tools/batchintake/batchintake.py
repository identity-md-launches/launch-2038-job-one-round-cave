#!/usr/bin/env python3
"""Check partial, out-of-order review-batch deliveries against verified ZTO inputs."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

SPEC = importlib.util.spec_from_file_location(
    "rewardbatch", Path(__file__).resolve().parents[1] / "rewardbatch" / "rewardbatch.py")
rb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rb)
rs, rr = rb.rs, rb.rr
SCHEMA = "batchintake-delivery-v1"
SCOPE = "review-file completeness only; not approval, entitlement, payment progress or replay protection"


def select(bundle, numbers):
    """Package copies of named batches; the check operation authenticates the source."""
    rs.require(isinstance(bundle, dict) and isinstance(bundle.get("batches"), list),
               "bundle must contain batches")
    rs.require(isinstance(numbers, list) and len(numbers) <= rs.MAX_CONTRIBUTORS,
               "numbers must be a bounded list")
    seen = set()
    packets = []
    for n in numbers:
        rs.require(type(n) is int and 1 <= n <= len(bundle["batches"]), "invalid batch number")
        rs.require(n not in seen, "duplicate batch number")
        seen.add(n)
        packets.append(bundle["batches"][n - 1])
    # Copy objects so edits to a delivery cannot mutate the caller's source.
    return json.loads(rr.canonical_bytes({"schema": SCHEMA,
                                         "bundle_sha256": rr.digest(bundle), "packets": packets}))


def check(request, report, metadata, bundle, delivery):
    """Recompute the source, then accept only exact distinct batches linked to it."""
    verified = rb.verify(request, report, metadata, bundle)
    rs.require(isinstance(delivery, dict) and set(delivery) == {"schema", "bundle_sha256", "packets"},
               "delivery must contain exactly schema, bundle_sha256 and packets")
    rs.require(delivery["schema"] == SCHEMA, "unsupported delivery schema")
    rs.require(delivery["bundle_sha256"] == rr.digest(bundle), "delivery is linked to another bundle")
    packets = delivery["packets"]
    rs.require(isinstance(packets, list) and len(packets) <= bundle["batch_count"],
               "packets must be a list no longer than the source batch count")
    seen = set()
    received_rows = received_units = 0
    for packet in packets:
        rs.require(isinstance(packet, dict), "packet must be an object")
        n = packet.get("number")
        rs.require(type(n) is int and 1 <= n <= bundle["batch_count"], "invalid packet number")
        rs.require(n not in seen, "duplicate packet number")
        expected = bundle["batches"][n - 1]
        rs.require(rr.canonical_bytes(packet) == rr.canonical_bytes(expected),
                   "packet differs from its verified source batch")
        seen.add(n)
        received_rows += expected["row_count"]
        received_units += int(expected["units"])
    missing = [n for n in range(1, bundle["batch_count"] + 1) if n not in seen]
    return {"schema": "batchintake-status-v1", "status": "incomplete" if missing else "complete",
            "bundle_sha256": verified["bundle_sha256"], "delivery_sha256": rr.digest(delivery),
            "report_sha256": verified["report_sha256"], "received_batches": sorted(seen),
            "missing_batches": missing, "received_rows": received_rows,
            "missing_rows": bundle["contributor_count"] - received_rows,
            "received_units": str(received_units),
            "missing_units": str(int(bundle["budget_units"]) - received_units),
            "budget_units": bundle["budget_units"], "scope": SCOPE}


def demo():
    request = rs.read_json(rr.ROOT / "example.json")
    metadata = rs.read_json(rr.ROOT / "zto-mainnet.json")
    report = rs.allocate(request, metadata)
    bundle = rb.build(request, report, metadata, 2)
    return {"demo": "Historical real ZTO metadata; illustrative address-free roles; no live balance or payment",
            "partial": check(request, report, metadata, bundle, select(bundle, [2])),
            "complete_out_of_order": check(request, report, metadata, bundle, select(bundle, [2, 1]))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")
    for command in ("select", "check"):
        p = sub.add_parser(command)
        p.add_argument("--bundle", required=True)
        p.add_argument("--output", help="new workspace JSON file; never overwrite")
        if command == "select":
            p.add_argument("--numbers", nargs="*", type=int, required=True,
                           help="batch numbers in transport order; empty is allowed")
        else:
            p.add_argument("--request", required=True)
            p.add_argument("--report", required=True)
            p.add_argument("--metadata", default=str(rr.ROOT / "zto-mainnet.json"))
            p.add_argument("--delivery", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo()
        elif args.command == "select":
            result = select(rs.read_json(args.bundle), args.numbers)
        else:
            result = check(rs.read_json(args.request), rs.read_json(args.report),
                           rs.read_json(args.metadata), rs.read_json(args.bundle), rs.read_json(args.delivery))
        rs.write_json(result, getattr(args, "output", None))
        return 1 if result.get("status") == "incomplete" else 0
    except (rs.Invalid, OSError, ValueError, OverflowError) as exc:
        print("batchintake: " + (str(exc) if isinstance(exc, rs.Invalid) else type(exc).__name__),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
