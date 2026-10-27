import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from urllib.parse import urlsplit

from .store import APIError, Store


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, status, payload, content_type='application/json; charset=utf-8', headers=None):
        if isinstance(payload, bytes):
            raw = payload
        else:
            raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise APIError(400, 'invalid content length')
        if not 0 < size <= 65536:
            raise APIError(400, 'invalid body size')
        try:
            return json.loads(self.rfile.read(size).decode('utf-8'))
        except (ValueError, UnicodeError):
            raise APIError(400, 'invalid JSON')

    def _dispatch(self):
        path = urlsplit(self.path).path
        if self.command == 'GET' and path == '/health':
            return self._send(200, {'status': 'ok'})
        header = self.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            raise APIError(401, 'authentication required')
        store = self.server.store
        user = store.authenticate(header[7:])
        if self.command == 'GET' and path == '/api/projects':
            return self._send(200, {'projects': store.projects(user['id'])})
        match = re.fullmatch(r'/api/projects/([1-9][0-9]*)/documents', path)
        if self.command == 'GET' and match:
            documents = store.project_documents(user['id'], int(match[1]))
            return self._send(200, {'documents': documents})
        match = re.fullmatch(r'/api/documents/([1-9][0-9]*)(/download)?', path)
        if match:
            document_id = int(match[1])
            if self.command == 'GET':
                document = store.document(user['id'], document_id)
                if match[2]:
                    return self._send(200, document['body'].encode('utf-8'),
                                      'text/plain; charset=utf-8',
                                      {'Content-Disposition': f'attachment; filename="document-{document_id}.txt"'})
                return self._send(200, document)
            if self.command == 'PATCH' and not match[2]:
                return self._send(200, store.update_document(user['id'], document_id, self._json_body()))
        raise APIError(404, 'route not found')

    def _handle(self):
        try:
            self._dispatch()
        except APIError as error:
            self._send(error.status, {'error': error.message})

    do_GET = _handle
    do_PATCH = _handle


def create_server(database, host='127.0.0.1', port=0):
    store = Store(database)
    store.initialize()
    server = ThreadingHTTPServer((host, port), Handler)
    server.store = store
    return server


def main():
    parser = argparse.ArgumentParser(description='Project documents HTTP service')
    parser.add_argument('--database', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    server = create_server(args.database, args.host, args.port)
    print(f'Listening on http://{args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
