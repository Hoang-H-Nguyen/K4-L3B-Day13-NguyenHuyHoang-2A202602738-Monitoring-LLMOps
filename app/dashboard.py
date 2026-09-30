"""Read-only dashboard aggregates from structured JSONL logs."""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return result.astimezone(timezone.utc)


def percentile(values: list[float], p: int) -> float | None:
    return sorted(values)[math.ceil(len(values) * p / 100) - 1] if values else None


def aggregate(path: Path, minutes: int = 60, end: datetime | None = None,
              latest: bool = False) -> dict:
    mode = "latest" if latest else "custom" if end is not None else "live"
    records = []
    skipped = 0
    if path.exists():
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    records.append((timestamp(record['ts']), record))
                except (ValueError, TypeError, KeyError, AttributeError):
                    skipped += 1
    last = max((ts for ts, _ in records), default=None)
    end = (last if latest and last else end) or datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    selected = [(ts, r) for ts, r in records if start < ts <= end and r.get('service') == 'api']
    received = [r for _, r in selected if r.get('event') == 'request_received']
    responses = [r for _, r in selected if r.get('event') == 'response_sent']
    failed = [r for _, r in selected if r.get('event') == 'request_failed']
    tools = [r for _, r in selected if r.get('tool_name') == 'retrieval'
             and isinstance(r.get('tool_success'), bool)]

    def numbers(rows, field):
        return [float(r[field]) for r in rows if isinstance(r.get(field), (int, float))
                and not isinstance(r[field], bool) and math.isfinite(r[field])]

    buckets = {}
    minute = start.replace(second=0, microsecond=0)
    while minute <= end:
        buckets[minute.isoformat()] = {'time': minute.isoformat(), 'requests': 0, 'cost': 0.0}
        minute += timedelta(minutes=1)
    for ts, r in selected:
        bucket = buckets[ts.replace(second=0, microsecond=0).isoformat()]
        bucket['requests'] += r.get('event') == 'request_received'
        if r.get('event') == 'response_sent':
            bucket['cost'] += sum(numbers([r], 'cost_usd'))
    latencies = numbers(responses, 'latency_ms')
    quality = numbers(responses, 'quality_score')
    return {
        'start': start.isoformat(), 'end': end.isoformat(), 'latest_log': last.isoformat() if last else None,
        'mode': mode,
        'source': 'data/logs.jsonl', 'file_exists': path.exists(), 'skipped_lines': skipped,
        'records': len(selected), 'requests': len(received), 'responses': len(responses),
        'latency': {f'p{p}': percentile(latencies, p) for p in (50, 95, 99)},
        'ttft_p95': percentile(numbers(responses, 'ttft_ms'), 95),
        'traffic_per_minute': len(received) / minutes,
        'error_rate': len(failed) / len(received) * 100 if received else None,
        'error_count': len(failed),
        'error_breakdown': dict(Counter(str(r.get('error_type', 'unknown')) for r in failed)),
        'retrieval_success': sum(r['tool_success'] for r in tools) / len(tools) * 100 if tools else None,
        'retrieval_attempts': len(tools),
        'cost': sum(numbers(responses, 'cost_usd')),
        'tokens_in': sum(numbers(responses, 'tokens_in')),
        'tokens_out': sum(numbers(responses, 'tokens_out')),
        'quality': sum(quality) / len(quality) if quality else None,
        'series': list(buckets.values()),
    }
