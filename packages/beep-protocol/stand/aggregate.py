#!/usr/bin/env python3
"""Fold the matrix runner's per-attempt event logs into one results file.

Reads the TSV index written by matrix-runner.sh, and for every attempt emits
each of that attempt's JSON event lines into a single results.jsonl, tagged
with the cell fields (network, entry, domain, profile, traffic kind, attempt
number) so a later analysis can group by cell and compare Beep against the
control download and the baseline.

Usage: aggregate.py INDEX_TSV OUT_JSONL
"""
import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: aggregate.py INDEX_TSV OUT_JSONL", file=sys.stderr)
        return 2
    index_path, out_path = sys.argv[1], sys.argv[2]

    cols = ["cell", "network", "entry", "port", "domain", "profile", "kind", "attempt", "event_log", "pcap"]
    written = 0
    with open(index_path, encoding="utf-8") as index, open(out_path, "w", encoding="utf-8") as out:
        for raw in index:
            line = raw.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < len(cols):
                continue
            row = dict(zip(cols, parts))
            try:
                with open(row["event_log"], encoding="utf-8") as ev:
                    for ev_line in ev:
                        ev_line = ev_line.strip()
                        if not ev_line:
                            continue
                        try:
                            event = json.loads(ev_line)
                        except json.JSONDecodeError:
                            continue
                        record = {
                            "cell": row["cell"],
                            "network": row["network"],
                            "entry": row["entry"],
                            "domain": row["domain"],
                            "profile": row["profile"],
                            "kind": row["kind"],
                            "attempt": int(row["attempt"]) if row["attempt"].isdigit() else row["attempt"],
                            "event": event,
                        }
                        out.write(json.dumps(record, ensure_ascii=False) + "\n")
                        written += 1
            except FileNotFoundError:
                continue

    print(f"aggregate: wrote {written} event records to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
