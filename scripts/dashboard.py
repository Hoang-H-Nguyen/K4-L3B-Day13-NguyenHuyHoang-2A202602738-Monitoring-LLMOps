"""Run the local, read-only lab dashboard: python scripts/dashboard.py."""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.dashboard import aggregate, timestamp
from scripts.validate_dashboard import load_dashboard_config


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path == '/':
                body = (ROOT / 'app/dashboard.html').read_bytes()
                content_type = 'text/html; charset=utf-8'
            elif url.path == '/api/dashboard':
                query = parse_qs(url.query)
                minutes = int(query.get('minutes', ['60'])[0])
                if not 1 <= minutes <= 10080:
                    raise ValueError('Time range must be between 1 minute and 7 days')
                end = timestamp(query['end'][0]) if query.get('end') else None
                config = load_dashboard_config(ROOT / 'config/dashboard.yaml')['dashboard']
                payload = aggregate(ROOT / 'data/logs.jsonl', minutes=minutes, end=end,
                                    latest=query.get('mode') == ['latest'])
                payload['config'] = config
                body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
                content_type = 'application/json; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, OSError) as exc:
            self.send_error(400, str(exc))

    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Dashboard: http://127.0.0.1:{args.port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
