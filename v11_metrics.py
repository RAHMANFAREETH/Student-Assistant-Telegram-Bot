"""Privacy-minimal, in-process measurements for V11 interactions ONLY.

No Telegram IDs, messages, documents, tokens or API keys are captured.
Metrics reset on Render restart and do not measure older tool latency.
"""
from __future__ import annotations
from collections import defaultdict, deque
from threading import RLock
from math import ceil
from time import monotonic

_LOCK = RLock()
_COUNTS = defaultdict(int)
_LATENCIES = defaultdict(lambda: deque(maxlen=128))
_START = monotonic()


def record(action: str, elapsed_ms: float) -> None:
    key = str(action or 'unknown')[:28]
    if key not in {'home', 'help', 'status', 'cancel', 'admin', 'button', 'perf'}:
        key = 'other'
    with _LOCK:
        _COUNTS[key] += 1
        _LATENCIES[key].append(max(0.0, min(float(elapsed_ms), 60000.0)))


def report() -> str:
    with _LOCK:
        counts = dict(_COUNTS)
        durations = {k: sorted(v) for k, v in _LATENCIES.items()}
    lines = ['📈 V11 Study Center — local performance',
             f'Worker uptime: {int(max(0, monotonic() - _START))} seconds',
             'Only V11 handler execution is measured (not Telegram/network delivery).']
    for key in sorted(counts):
        sample = durations[key]
        median = sample[len(sample)//2] if sample else 0.0
        p95 = sample[max(0, ceil(len(sample)*0.95)-1)] if sample else 0.0
        lines.append(f'• {key}: {counts[key]} uses, median {median:.1f} ms, p95 {p95:.1f} ms')
    if not counts:
        lines.append('No V11 interactions recorded yet.')
    lines.append('Metrics are per-worker, in memory and reset on redeploy.')
    return '\n'.join(lines)
