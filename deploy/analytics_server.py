"""Private loopback service for website traffic reports. Serve publicly via HTTPS nginx."""
import argparse
import json
import os
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UUID4 = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
KINDS = ('view', 'master', 'phone', 'link')


def valid_event(event):
    if not isinstance(event, dict):
        return False
    if any(not isinstance(event.get(key), str) for key in ('id', 'visitor', 'kind', 'page', 'target')):
        return False
    return (
        UUID4.fullmatch(event['id']) and UUID4.fullmatch(event['visitor'])
        and event['kind'] in KINDS
        and event['page'].startswith('/') and len(event['page']) <= 240
        and '?' not in event['page'] and len(event['target']) <= 240
        and '?' not in event['target']
        and bool(event['target']) == (event['kind'] == 'link')
    )


def initialize(database):
    with closing(sqlite3.connect(database)) as db, db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, visitor TEXT NOT NULL, kind TEXT NOT NULL,
                page TEXT NOT NULL, target TEXT NOT NULL,
                created INTEGER NOT NULL DEFAULT (unixepoch())
            )
        ''')
        db.execute('CREATE INDEX IF NOT EXISTS events_created ON events(created)')


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload=None):
        body = b'' if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        if self.path != '/api/analytics/event':
            return self.respond(404)
        if self.headers.get('Origin') != self.server.site_origin:
            return self.respond(403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.respond(400)
        if not 0 < size <= 2048:
            return self.respond(413)
        try:
            event = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeError):
            return self.respond(400)
        if not valid_event(event):
            return self.respond(400)
        with closing(sqlite3.connect(self.server.database)) as db, db:
            db.execute('DELETE FROM events WHERE created < unixepoch() - 90 * 86400')
            db.execute('''
                INSERT OR IGNORE INTO events (id, visitor, kind, page, target)
                VALUES (:id, :visitor, :kind, :page, :target)
            ''', event)
        self.respond(204)

    def do_GET(self):
        match = re.fullmatch(r'/api/analytics/report\?days=(1|7|30|90)', self.path)
        if not match:
            return self.respond(404)
        seconds = int(match[1]) * 86400
        with closing(sqlite3.connect(self.server.database)) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            totals = db.execute('''
                SELECT kind, count(*) AS total, count(DISTINCT visitor) AS visitors
                FROM events WHERE created >= unixepoch() - ? GROUP BY kind
            ''', (seconds,))
            groups = db.execute('''
                SELECT kind, CASE WHEN kind = 'view' THEN page ELSE target END AS label,
                       count(*) AS total, count(DISTINCT visitor) AS visitors
                FROM events WHERE created >= unixepoch() - ? AND kind IN ('view', 'link')
                GROUP BY kind, label ORDER BY total DESC, label LIMIT 200
            ''', (seconds,))
            report = {'totals': [dict(row) for row in totals], 'details': [dict(row) for row in groups]}
        self.respond(200, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8002)
    args = parser.parse_args()
    origin = os.environ.get('ANALYTICS_SITE_ORIGIN', '')
    if not re.fullmatch(r'https://[^/?#]+', origin):
        parser.error('Set ANALYTICS_SITE_ORIGIN (HTTPS origin).')
    os.umask(0o077)
    initialize(args.database)
    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.database = args.database
        server.site_origin = origin
        server.serve_forever()


if __name__ == '__main__':
    main()
