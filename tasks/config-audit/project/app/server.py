"""Synthetic records service. Authentication belongs to the reverse proxy."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

DATA_FILE = Path(os.environ.get('DATA_FILE', '/var/lib/records/records.json'))
LOCK = Lock()


def read_records():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/health':
            self.send_json(200, {'status': 'ok'})
        elif path == '/api/records':
            with LOCK:
                self.send_json(200, {'records': read_records()})
        elif path == '/internal/status':
            self.send_json(200, {'service': 'records', 'data_file': str(DATA_FILE),
                                 'maintenance_key': 'DEMO-MAINTENANCE-a62f'})
        else:
            self.send_json(404, {'error': 'not found'})

    def do_POST(self):
        if urlsplit(self.path).path != '/api/records':
            self.send_json(404, {'error': 'not found'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise ValueError('invalid size')
            payload = json.loads(self.rfile.read(length))
            text = payload.get('text') if isinstance(payload, dict) else None
            if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                raise ValueError('invalid text')
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {'error': 'invalid record'})
            return
        with LOCK:
            records = read_records()
            record = {'id': max((r['id'] for r in records), default=0) + 1, 'text': text}
            records.append(record)
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            temporary = DATA_FILE.with_suffix('.tmp')
            temporary.write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
            temporary.replace(DATA_FILE)
        self.send_json(201, record)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', 8000), Handler)
    server.serve_forever()
