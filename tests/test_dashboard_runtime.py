import json
import pytest
from datetime import datetime, timezone

from app.dashboard import aggregate


def test_window_metrics_and_retrieval_include_successful_responses(tmp_path):
    log = tmp_path / 'logs.jsonl'
    def row(ts, event, **fields):
        return {'ts': '2026-09-30T'+ts+'Z', 'service': 'api', 'event': event, **fields}
    rows = [
        row('09:00:00', 'request_received'),  # excluded at open left boundary
        row('09:30:00', 'request_received'),
        row('09:30:01', 'response_sent', latency_ms=100, ttft_ms=10, cost_usd=.01,
            tokens_in=10, tokens_out=20, quality_score=.8, tool_name='retrieval', tool_success=True),
        row('09:31:00', 'request_received'),
        row('09:31:01', 'response_sent', latency_ms=300, ttft_ms=20, cost_usd=.02,
            tokens_in=30, tokens_out=40, quality_score=1., tool_name='retrieval', tool_success=True),
        row('09:32:00', 'request_received'),
        row('10:00:00', 'request_failed', error_type='RuntimeError', tool_name='retrieval', tool_success=False),
        row('10:00:01', 'request_received'),  # future event excluded
    ]
    log.write_text('\n'.join(json.dumps(r) for r in rows)+'\n{partial')
    result = aggregate(log, end=datetime(2026,9,30,10,tzinfo=timezone.utc))
    assert result['requests'] == 3
    assert result['responses'] == 2
    assert result['latency'] == {'p50': 100, 'p95': 300, 'p99': 300}
    assert result['ttft_p95'] == 20
    assert result['error_rate'] == pytest.approx(100 / 3)
    assert result['retrieval_success'] == pytest.approx(200 / 3)
    assert result['error_breakdown'] == {'RuntimeError': 1}
    assert result['cost'] == .03
    assert result['quality'] == .9
    assert result['tokens_in'] == 40 and result['tokens_out'] == 60
    assert sum(b['requests'] for b in result['series']) == 3
    assert sum(b['cost'] for b in result['series']) == .03
    assert result['skipped_lines'] == 1
    assert result['mode'] == 'custom'


def test_empty_and_latest_window_do_not_fabricate_success(tmp_path):
    log = tmp_path / 'logs.jsonl'
    empty = aggregate(log)
    assert empty['quality'] is None and empty['error_rate'] is None
    assert empty['retrieval_success'] is None and empty['latency']['p95'] is None
    assert empty['mode'] == 'live'
    log.write_text(json.dumps({'service':'api','event':'request_received','ts':'2026-09-30T10:00:00Z'}))
    latest = aggregate(log, latest=True)
    assert latest['end'] == '2026-09-30T10:00:00+00:00'
    assert latest['requests'] == 1
    assert latest['retrieval_success'] is None
    assert latest['mode'] == 'latest'
