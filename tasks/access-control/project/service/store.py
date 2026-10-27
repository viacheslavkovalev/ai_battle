from contextlib import contextmanager
from pathlib import Path
import sqlite3


class APIError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


class Store:
    def __init__(self, database):
        self.database = str(database)

    def initialize(self):
        path = Path(self.database)
        if not path.exists() or path.stat().st_size == 0:
            with self.connection() as db:
                db.executescript(Path(__file__).with_name('seed.sql').read_text(encoding='utf-8'))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def authenticate(self, token):
        with self.connection() as db:
            user = db.execute('SELECT id, name FROM users WHERE token = ?', (token,)).fetchone()
        if user is None:
            raise APIError(401, 'authentication required')
        return dict(user)

    def projects(self, user_id):
        with self.connection() as db:
            rows = db.execute('''
                SELECT p.id, p.name, m.role FROM projects p
                JOIN memberships m ON m.project_id = p.id
                WHERE m.user_id = ? ORDER BY p.id
            ''', (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def project_documents(self, user_id, project_id):
        with self.connection() as db:
            member = db.execute('''
                SELECT role FROM memberships WHERE user_id = ? AND project_id = ?
            ''', (user_id, project_id)).fetchone()
            if member is None:
                raise APIError(404, 'project not found')
            rows = db.execute('''
                SELECT id, project_id, title FROM documents
                WHERE project_id = ? ORDER BY id
            ''', (project_id,)).fetchall()
        return [dict(row) for row in rows]

    def _document(self, db, user_id, document_id):
        row = db.execute('''
            SELECT d.id, d.project_id, d.title, d.body, m.role
            FROM documents d
            JOIN memberships m ON m.user_id = ?
            WHERE d.id = ?
            ORDER BY m.project_id LIMIT 1
        ''', (user_id, document_id)).fetchone()
        if row is None:
            raise APIError(404, 'document not found')
        return dict(row)

    def document(self, user_id, document_id):
        with self.connection() as db:
            document = self._document(db, user_id, document_id)
        document.pop('role')
        return document

    def update_document(self, user_id, document_id, changes):
        with self.connection() as db:
            document = self._document(db, user_id, document_id)
            if document['role'] not in ('editor', 'admin'):
                raise APIError(403, 'read-only membership')
            if not isinstance(changes, dict) or not changes or set(changes) - {'title', 'body'}:
                raise APIError(400, 'provide title and/or body')
            for key, value in changes.items():
                limit = 200 if key == 'title' else 20000
                if not isinstance(value, str) or len(value) > limit or (key == 'title' and not value.strip()):
                    raise APIError(400, 'invalid document fields')
            title = changes.get('title', document['title'])
            body = changes.get('body', document['body'])
            db.execute('UPDATE documents SET title = ?, body = ? WHERE id = ?',
                       (title, body, document_id))
            return {'id': document_id, 'project_id': document['project_id'], 'title': title, 'body': body}
