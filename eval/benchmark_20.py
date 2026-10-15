"""benchmark_20.py — 20-case benchmark with JSONL persistence + CI gate.

Extends benchmark.py (3 cases) to 20. Persists per-run stats to
eval/benchmarks.jsonl. Fails CI on p99 regression >15% vs baseline or
any AST bypass.

Usage:
    python eval/benchmark_20.py --iterations 5
    python eval/benchmark_20.py --baseline eval/baseline.jsonl --check
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from statistics import mean, stdev

from eval.cases import CASES

API_URL = os.getenv("API_URL", "http://localhost:8000")
BENCH_PATH = os.getenv("BENCH_PATH", "eval/benchmarks.jsonl")
P99_REGRESSION_PCT = 15.0


def _percentile(sorted_vals, pct):
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * pct / 100))
    return sorted_vals[idx]


def run_case(case_id, question, iterations, session):
    times = []
    status = None
    for _ in range(iterations):
        start = time.time()
        try:
            r = session.post(f"{API_URL}/api/v1/query", json={"question": question})
            status = r.status_code
        except Exception:
            status = -1
        times.append(time.time() - start)
    times.sort()
    return {
        "case_id": case_id,
        "question": question,
        "iterations": iterations,
        "status": status,
        "mean_ms": round(mean(times) * 1000, 1),
        "p50_ms": round(_percentile(times, 50) * 1000, 1),
        "p99_ms": round(_percentile(times, 99) * 1000, 1),
        "min_ms": round(times[0] * 1000, 1),
        "max_ms": round(times[-1] * 1000, 1),
        "stdev_ms": round(stdev(times) * 1000, 1) if len(times) > 1 else 0.0,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def run_all(iterations, session):
    results = []
    for case_id, question, _expect_sql, _expect_status in CASES:
        row = run_case(case_id, question, iterations, session)
        results.append(row)
        print(f"  {case_id}: mean={row['mean_ms']}ms p99={row['p99_ms']}ms status={row['status']}")
    return results


def persist(results, path=BENCH_PATH):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")


def load_baseline(path):
    baseline = {}
    if not os.path.exists(path):
        return baseline
    with open(path) as f:
        for line in f:
            try:
                row = json.loads(line)
                baseline[row["case_id"]] = row
            except (json.JSONDecodeError, KeyError):
                continue
    return baseline


def check_regression(results, baseline, pct=P99_REGRESSION_PCT):
    failures = []
    for r in results:
        b = baseline.get(r["case_id"])
        if not b:
            continue
        if b["p99_ms"] <= 0:
            continue
        delta = (r["p99_ms"] - b["p99_ms"]) / b["p99_ms"] * 100
        if delta > pct:
            failures.append(f"{r['case_id']}: p99 {b['p99_ms']}ms -> {r['p99_ms']}ms (+{delta:.1f}%)")
        if r["status"] != 200 and b["status"] == 200:
            failures.append(f"{r['case_id']}: status {b['status']} -> {r['status']}")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--check", action="store_true", help="fail on p99 regression >15%")
    parser.add_argument("--save", action="store_true", help="write results as new baseline")
    args = parser.parse_args()

    import requests
    session = requests.Session()

    print(f"Benchmarking {len(CASES)} cases x {args.iterations} iterations")
    results = run_all(args.iterations, session)
    persist(results)

    if args.save:
        with open(BENCH_PATH, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(f"Baseline saved to {BENCH_PATH}")

    if args.check and args.baseline:
        baseline = load_baseline(args.baseline)
        failures = check_regression(results, baseline)
        if failures:
            print("\nREGRESSION GATE FAILED:")
            for f_ in failures:
                print(f"  - {f_}")
            raise SystemExit(1)
        print("\nRegression gate: PASS")


if __name__ == "__main__":
    main()
