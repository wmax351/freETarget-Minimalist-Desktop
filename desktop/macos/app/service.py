from __future__ import annotations
import json
import secrets
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from storage import StorageConflict
import freetarget_bridge as bridge

MAX_REQUEST = 128 * 1024 * 1024


def safe_script_json(value):
    # Prevent stored text from terminating the bootstrap script element.
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


class DesktopHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, controller, address=('127.0.0.1', 0)):
        self.controller = controller
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, DesktopHandler)
        self.host = '127.0.0.1:' + str(self.server_address[1])
        self.origin = 'http://' + self.host
        self.app_path = '/app/' + self.token + '/'
        self.url = self.origin + self.app_path

    def html_bytes(self):
        state = self.controller.store.snapshot()
        boot = dict(token=self.token, origin=self.origin, revision=state['revision'], storage=state['storage'])
        script = (self.controller.assets / 'desktop_bootstrap.js').read_text(encoding='utf-8')
        script = script.replace('/*__FT_DESKTOP_BOOT__*/', safe_script_json(boot), 1)
        html = (self.controller.assets / 'index.html').read_text(encoding='utf-8')
        sync = self.controller.assets / 'apple_sync.js'
        if sync.is_file():
            html = html.replace('<!--APPLE_PROFILE_SYNC-->', '<script>' + sync.read_text(encoding='utf-8') + '</script>', 1)
        return html.replace('<!--DESKTOP_BOOTSTRAP-->', '<script>' + script + '</script>', 1).encode('utf-8')


class DesktopHandler(bridge.Handler):
    def end_headers(self):
        for name, value in [
            ('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'),
            ('Referrer-Policy', 'no-referrer'), ('Cache-Control', 'no-store'),
            ('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")]:
            self.send_header(name, value)
        super().end_headers()

    def authorized(self, page=False):
        if self.headers.get('Host') != self.server.host:
            self.respond(dict(error='Invalid local host.'), 403)
            return False
        origin = self.headers.get('Origin')
        if origin and origin != self.server.origin:
            self.respond(dict(error='Invalid request origin.'), 403)
            return False
        if page:
            return True
        token = self.headers.get('X-FT-Session', '')
        if not secrets.compare_digest(token.encode('utf-8'), self.server.token.encode('ascii')):
            self.respond(dict(error='This desktop session is not authorized.'), 403)
            return False
        return True

    def do_OPTIONS(self):
        self.respond(dict(error='Cross-origin requests are not supported.'), 403)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == self.server.app_path:
            if not self.authorized(page=True):
                return
            try:
                data = self.server.html_bytes()
            except (OSError, ValueError) as exc:
                return self.respond(dict(error='Could not load the desktop interface: ' + str(exc)), 500)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if not self.authorized():
            return
        if path == '/desktop/info':
            return self.respond(self.server.controller.info())
        if path in {'/api/events', '/api/serial-ports'}:
            return super().do_GET()
        self.respond(dict(error='Not found'), 404)

    def read_object(self):
        length = int(self.headers.get('Content-Length', '0'))
        if not 1 <= length <= MAX_REQUEST:
            raise ValueError('Invalid desktop request size.')
        from storage import strict_json
        obj = strict_json(self.rfile.read(length))
        if not isinstance(obj, dict):
            raise ValueError('The desktop request must be a JSON object.')
        return obj

    def do_POST(self):
        if not self.authorized():
            return
        path = urlsplit(self.path).path
        if path.startswith('/api/'):
            return super().do_POST()
        try:
            obj = self.read_object()
            controller = self.server.controller
            if path == '/desktop/store':
                result = controller.store.change(obj.get('key'), obj.get('value'), remove=obj.get('remove') is True,
                                                 expected_revision=obj.get('expected_revision'))
            elif path == '/desktop/apple-sync-read':
                result = controller.apple_sync_read(obj)
            elif path == '/desktop/apple-sync-apply':
                result = controller.apple_sync_apply(obj)
            elif path == '/desktop/export-backup':
                result = controller.export_backup()
            elif path == '/desktop/preview-backup':
                result = controller.preview_backup()
            elif path == '/desktop/restore-backup':
                result = controller.restore_backup(obj)
            elif path == '/desktop/open-data-folder':
                result = controller.open_data_folder()
            elif path == '/desktop/browser-exporter':
                result = controller.start_browser_exporter()
            else:
                return self.respond(dict(error='Not found'), 404)
            self.respond(result)
        except StorageConflict as exc:
            self.respond(dict(error=str(exc)), 409)
        except (ValueError, TypeError, UnicodeError, OSError) as exc:
            self.respond(dict(error=str(exc)), 400)
        except Exception:
            import logging
            logging.exception('Desktop operation failed')
            self.respond(dict(error='The desktop operation failed. Data was not replaced. See the app log.'), 500)
