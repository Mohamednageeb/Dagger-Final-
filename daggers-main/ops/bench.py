#!/usr/bin/env python3
"""Daggers micro-benchmark — offline paths only (no network, temporary database).

    python3 ops/bench.py            # or: make bench

Measures, on THIS machine:
  · offline scan (the Chrome extension's POST /api/scan path: engine + central verdict, no live lookups)
  · Guard index lookup (exact and parent-site match)
  · DoH resolution of a blocked name (parse + lookup + answer, no upstream)
Numbers depend on the machine; they are printed, never stored or claimed elsewhere.
"""
from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.guard.doh import DoHResolver, build_query  # noqa: E402
from backend.app.main import Runtime  # noqa: E402


def timed(fn, n: int) -> tuple[float, float]:
    samples = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    samples.sort()
    return statistics.median(samples), samples[int(len(samples) * 0.95) - 1]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        settings = Settings(db_path=tmp_path / "bench.db", evidence_dir=tmp_path / "ev",
                            gallery_dir=tmp_path / "gal", web_dir=ROOT / "web", guard_sync_debounce_s=60.0)
        rt = Runtime(settings)
        urls = ["https://adcb-secure-login.xyz/login", "https://example.org/", "https://emiratespost-uae.top/pay"]
        rt.scan("url", urls[0], "en")                                     # warm-up (loads data files)
        i = {"n": 0}

        def one_scan():
            rt.scan("url", urls[i["n"] % len(urls)], "en")
            i["n"] += 1

        med, p95 = timed(one_scan, 200)
        print(f"offline scan (engine + verdict policy): median {med:.2f} ms · p95 {p95:.2f} ms  (n=200)")

        rows = [{"domain": f"fake-{k}.xyz", "source": "radar"} for k in range(50_000)]
        rt.guard.index.replace(rows)
        med, p95 = timed(lambda: rt.guard.index.match("login.www.fake-49999.xyz"), 20_000)
        print(f"Guard lookup, 50,000 listed domains (parent match): median {med * 1000:.1f} µs · p95 {p95 * 1000:.1f} µs")
        med, p95 = timed(lambda: rt.guard.index.match("not-listed.example.org"), 20_000)
        print(f"Guard lookup, not listed:                            median {med * 1000:.1f} µs · p95 {p95 * 1000:.1f} µs")

        resolver = DoHResolver(lookup=rt.guard.index.match, on_block=lambda d: None, upstream="unused")
        query = build_query("www.fake-123.xyz")
        med, p95 = timed(lambda: resolver.resolve(query), 20_000)
        print(f"DoH answer for a blocked name (no upstream):          median {med * 1000:.1f} µs · p95 {p95 * 1000:.1f} µs")
        rt.repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
