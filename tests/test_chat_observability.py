from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True


def test_request_ids_and_context_are_isolated(monkeypatch, tmp_path):
    import re
    from app import main
    from app.agent import AgentResult
    from app.pii import hash_user_id
    from structlog.contextvars import bind_contextvars

    path = tmp_path / 'requests.jsonl'
    monkeypatch.setattr(logging_config, 'LOG_PATH', path)
    calls = []

    def run(**kwargs):
        calls.append(kwargs)
        return AgentResult('safe answer', 1, 1, 1, 1, 0.0, 0.9)

    monkeypatch.setattr(main.agent, 'run', run)

    async def requests():
        bind_contextvars(stale_context='must disappear')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await asyncio.gather(*[
                client.post('/chat', headers=headers, json={
                    'user_id': f'user-{i}', 'session_id': f'session-{i}',
                    'feature': 'qa', 'message': 'Explain logging',
                })
                for i, headers in enumerate([
                    {'x-request-id': 'req-ab12cd34'}, {},
                    {'x-request-id': 'invalid@example.com'},
                ])
            ])

    responses = asyncio.run(requests())
    records = [json.loads(line) for line in path.read_text().splitlines()]
    ids = []
    for i, response in enumerate(responses):
        assert response.status_code == 200
        cid = response.headers['x-request-id']
        ids.append(cid)
        assert re.fullmatch(r'req-[0-9a-f]{8}', cid)
        assert response.json()['correlation_id'] == cid
        assert float(response.headers['x-response-time-ms']) >= 0
        assert next(c for c in calls if c['session_id'] == f'session-{i}')['correlation_id'] == cid
        events = [r for r in records if r['correlation_id'] == cid]
        assert {r['event'] for r in events} == {'request_received', 'response_sent'}
        for event in events:
            assert event['user_id_hash'] == hash_user_id(f'user-{i}')
            assert event['session_id'] == f'session-{i}'
            assert event['model'] == main.agent.model
            assert event['feature'] == 'qa'
            assert event['env']
            assert 'stale_context' not in event
    assert ids[0] == 'req-ab12cd34'
    assert len(set(ids)) == 3
