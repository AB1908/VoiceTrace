"""Simple metrics summary for processing runs."""
from __future__ import annotations

import json
from pathlib import Path

from config import Config


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    rows = _load_rows(Config.metrics_file())
    if not rows:
        print(f"No metrics found at {Config.metrics_file()}")
        return

    total = len(rows)
    success = [r for r in rows if r.get("status") == "success"]
    failed = [r for r in rows if r.get("status") == "failed"]
    raw_only = [r for r in rows if r.get("raw_only") is True and r.get("status") == "success"]

    totals = [float(r.get("durations_sec", {}).get("total", 0.0)) for r in success]
    cleanup = [float(r.get("durations_sec", {}).get("cleanup", 0.0)) for r in success if "cleanup" in r.get("durations_sec", {})]
    breakdown = [float(r.get("durations_sec", {}).get("breakdown", 0.0)) for r in success if "breakdown" in r.get("durations_sec", {})]
    compression = [float(r.get("compression_ratio", 0.0)) for r in success if "compression_ratio" in r]

    print("Metrics Summary")
    print(f"- metrics file: {Config.metrics_file()}")
    print(f"- total runs: {total}")
    print(f"- successful runs: {len(success)}")
    print(f"- failed runs: {len(failed)}")
    print(f"- raw-only runs: {len(raw_only)}")
    print(f"- avg total seconds (success): {_avg(totals):.2f}")
    if cleanup:
        print(f"- avg cleanup seconds: {_avg(cleanup):.2f}")
    if breakdown:
        print(f"- avg breakdown seconds: {_avg(breakdown):.2f}")
    if compression:
        print(f"- avg compression ratio (clean/raw chars): {_avg(compression):.3f}")


if __name__ == "__main__":
    main()
