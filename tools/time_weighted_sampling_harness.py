"""
time_weighted_sampling_harness.py

Simulate the TIME_WEIGHTED_RANDOM sampling method used in `src/main.py`.
This uses the power-transform:
    if weight <= 0: t = u
    else: t = 1 - (1 - u) ** (1 + weight)
and then maps to an integer block via: chosen = int(a + t * (b - a)) clamped to [a,b].

Run examples:
    python tools/time_weighted_sampling_harness.py --a 3250000 --b 3258640 --weights 0,0.5,1,2 --samples 200000

This prints per-weight statistics: mean normalized position (0=old,1=recent), quantiles,
proportion in top X% and a decile histogram.
"""
from __future__ import annotations
import argparse
import math
import random
import statistics
import sys
from typing import List


def sample_time_weighted(a: int, b: int, weight: float, rng: random.Random) -> int:
    """Sample according to TIME_WEIGHTED_RANDOM mapping used in main.py.

    - u ~ Uniform(0,1)
    - if weight <= 0: t = u
      else: t = 1 - (1 - u) ** (1 + weight)
    - chosen = int(a + t * (b - a)), then clamp to [a,b]
    """
    if b < a:
        raise ValueError("b must be >= a")
    u = rng.random()
    if weight <= 0:
        t = u
    else:
        t = 1.0 - (1.0 - u) ** (1.0 + weight)
    # Map continuous t in [0,1) to an inclusive integer in [a, b] using N = b-a+1
    N = (b - a) + 1
    idx = int(math.floor(t * N))
    if idx < 0:
        idx = 0
    elif idx >= N:
        idx = N - 1
    return a + idx


def compute_quantiles(samples: List[int], quantiles: List[float]) -> List[int]:
    if not samples:
        return [0 for _ in quantiles]
    s = sorted(samples)
    n = len(s)
    results = []
    for p in quantiles:
        if p <= 0:
            results.append(s[0])
        elif p >= 1:
            results.append(s[-1])
        else:
            idx = int(p * (n - 1))
            results.append(s[idx])
    return results


def run_simulation(a: int, b: int, weights: List[float], samples_per_w: int, seed: int, top_percent: float):
    rng = random.Random(seed)
    N = (b - a) if b > a else 1
    quantile_points = [0.1, 0.25, 0.5, 0.75, 0.9]

    print(f"Sampling range: a={a}, b={b} (b-a={b-a})")
    print(f"samples per weight: {samples_per_w}, seed: {seed}\n")

    for w in weights:
        chosen = [sample_time_weighted(a, b, w, rng) for _ in range(samples_per_w)]
        norm = [(x - a) / (b - a) if b > a else 0.0 for x in chosen]
        mean_norm = statistics.mean(norm) if norm else 0.0
        qvals = compute_quantiles(chosen, quantile_points)
        top_threshold = a + int(((100.0 - top_percent) / 100.0) * (b - a))
        top_count = sum(1 for x in chosen if x >= top_threshold)
        top_prop = top_count / samples_per_w

        print(f"weight={w}: mean_norm={mean_norm:.4f}, top_{int(top_percent)}%_prop={top_prop:.4f}")
        qpairs = [f"{int(p*100)}%={q}" for p, q in zip(quantile_points, qvals)]
        print("    Quantiles: " + ", ".join(qpairs))
        # decile histogram
        buckets = [0] * 10
        for v in norm:
            bi = min(9, int(v * 10))
            buckets[bi] += 1
        hist = ",".join(str(int(x)) for x in buckets)
        print(f"    Decile counts (old->recent): {hist}\n")


def parse_weights(wstr: str) -> List[float]:
    parts = [p.strip() for p in wstr.split(",") if p.strip()]
    vals = []
    for p in parts:
        try:
            vals.append(float(p))
        except Exception:
            print(f"Warning: couldn't parse weight '{p}', skipping.")
    return vals


def main(argv=None):
    p = argparse.ArgumentParser(description="TIME_WEIGHTED_RANDOM sampling harness")
    p.add_argument("--a", type=int, required=True, help="start block (defaultStartBlock)")
    p.add_argument("--b", type=int, required=True, help="end block (oneDayOld) - inclusive upper bound")
    p.add_argument("--weights", type=str, default="0,0.5,1,2",
                   help="comma-separated stream_time_weight values to test, e.g. '0,0.5,1,2'")
    p.add_argument("--samples", type=int, default=100000, help="samples per weight (default: 100000)")
    p.add_argument("--seed", type=int, default=12345, help="random seed")
    p.add_argument("--top-percent", type=float, default=10.0, help="report proportion in top X percent of range")

    args = p.parse_args(argv)
    weights = parse_weights(args.weights)
    if not weights:
        print("No valid weights provided. Exiting.")
        sys.exit(2)
    if args.b < args.a:
        print("Error: b must be >= a")
        sys.exit(2)

    run_simulation(args.a, args.b, weights, args.samples, args.seed, args.top_percent)


if __name__ == "__main__":
    main()
