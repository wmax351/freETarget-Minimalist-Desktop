import http.client
import json
import pathlib
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
from controller import DesktopController
from desktop import CloseCoordinator
from platform_support import InstanceLock
from service import DesktopHTTPServer
from storage import DataStore, StorageConflict, read_backup
import freetarget_bridge as bridge

ASSETS = pathlib.Path(__file__).resolve().parents[1] / 'app/assets'


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = DataStore(self.temp.name)
        self.bridge = SimpleNamespace(lock=threading.RLock(), state={'connected': False, 'connecting': False})
        self.controller = DesktopController(self.store, self.bridge, ASSETS)
        self.window = Mock()
        self.window.evaluate_js.return_value = {'active': False, 'unsaved': False}
        self.controller.window = self.window
        self.controller.webview = SimpleNamespace(FileDialog=SimpleNamespace(OPEN=1, SAVE=2))
        self.import_path = pathlib.Path(self.temp.name) / 'input.json'
        self.import_path.write_text(json.dumps(dict(format='freetarget-browser-export', schema=1, storage={'ft-theme': 'dark'})))
        self.window.create_file_dialog.return_value = (str(self.import_path),)

    def preview(self):
        return self.controller.preview_backup()

    def restore_args(self, preview):
        return dict(import_id=preview['import_id'], expected_revision=preview['expected_revision'], confirmed=True)

    def test_preview_requires_native_selection_and_confirmation(self):
        result = self.preview()
        self.assertEqual(result['incoming']['preferences'], 1)
        self.assertEqual(self.store.snapshot()['storage'], {})
        args = self.restore_args(result)
        with self.assertRaises(ValueError):
            self.controller.restore_backup({**args, 'confirmed': False})
        self.controller.restore_backup(args)
        self.assertEqual(self.store.snapshot()['storage'], {'ft-theme': 'dark'})
        with self.assertRaises(ValueError):
            self.controller.restore_backup(args)

    def test_cancel_and_invalid_import_leave_current_data(self):
        self.window.create_file_dialog.return_value = None
        self.assertEqual(self.preview(), {'cancelled': True})
        self.assertEqual(self.controller.export_backup(), {'cancelled': True})
        self.window.create_file_dialog.return_value = (str(self.import_path),)
        self.import_path.write_text('invalid-json')
        with self.assertRaises(ValueError):
            self.preview()
        self.assertEqual(self.store.snapshot()['storage'], {})

    def test_live_session_and_connected_target_cannot_preview_or_restore(self):
        preview = self.preview()
        for state in ({'active': True}, {'unsaved': True}, None):
            self.window.evaluate_js.return_value = state
            with self.assertRaises(ValueError):
                self.preview()
            with self.assertRaises(ValueError):
                self.controller.restore_backup(self.restore_args(preview))
        self.window.evaluate_js.return_value = {'active': False, 'unsaved': False}
        for field in ('connected', 'connecting'):
            self.bridge.state[field] = True
            with self.assertRaises(ValueError):
                self.preview()
            with self.assertRaises(ValueError):
                self.controller.restore_backup(self.restore_args(preview))
            self.bridge.state[field] = False

    def test_expired_stale_and_wrong_preview_rejected(self):
        preview = self.preview()
        args = self.restore_args(preview)
        with self.assertRaises(ValueError):
            self.controller.restore_backup({**args, 'import_id': 'wrong'})
        with patch('controller.time.monotonic', return_value=float('inf')):
            with self.assertRaises(ValueError):
                self.controller.restore_backup(args)
        self.store.change('ft-theme', 'light', expected_revision=0)
        with self.assertRaises(StorageConflict):
            self.controller.restore_backup(args)
        self.assertEqual(self.store.snapshot()['storage']['ft-theme'], 'light')

    def test_export_adds_extension_and_writes_valid_snapshot(self):
        self.store.change('ft-theme', 'dark', expected_revision=0)
        target = pathlib.Path(self.temp.name) / 'my-backup'
        self.window.create_file_dialog.return_value = str(target)
        self.assertEqual(self.controller.export_backup()['filename'], 'my-backup.json')
        self.assertEqual(read_backup(target.with_suffix('.json').read_bytes())[0], {'ft-theme': 'dark'})

    def test_sync_export_omits_connection_settings_and_import_merge_preserves_local_connection(self):
        profiles = json.dumps([{'id': 'p-1', 'name': 'Alex', 'guns': []}])
        history = json.dumps([{'id': 's-1', 'name': 'Alex'}])
        self.store.change('ft-shooter-profiles-v1', profiles, expected_revision=0)
        self.store.change('ft-session-history-v1', history, expected_revision=1)
        self.store.change('ft-host', '192.168.10.9', expected_revision=2)
        target = pathlib.Path(self.temp.name) / 'portable-sync'
        self.window.create_file_dialog.return_value = str(target)
        exported = self.controller.export_sync_file()
        sync_path = target.with_suffix('.json')
        self.assertEqual(exported['filename'], sync_path.name)
        document = json.loads(sync_path.read_text(encoding='utf-8'))
        self.assertEqual(document['data']['profiles'], json.loads(profiles))
        self.assertNotIn('ft-host', document['data']['settings'])

        imported_profiles = json.dumps([{'id': 'p-1', 'name': 'Alex', 'guns': []},
                                        {'id': 'p-2', 'name': 'Morgan', 'guns': []}])
        sync_path.write_text(json.dumps({
            **document,
            'data': {**document['data'], 'profiles': json.loads(imported_profiles),
                     'settings': {**document['data']['settings'], 'ft-theme-mode': None}},
        }), encoding='utf-8')
        self.window.create_file_dialog.return_value = str(sync_path)
        preview = self.controller.read_sync_file()
        self.assertEqual(preview['expected_revision'], 3)
        self.controller.apply_sync({
            'expected_revision': preview['expected_revision'],
            'updates': {'ft-shooter-profiles-v1': imported_profiles, 'ft-theme-mode': None},
        })
        state = self.store.snapshot()['storage']
        self.assertEqual(json.loads(state['ft-shooter-profiles-v1'])[-1]['name'], 'Morgan')
        self.assertEqual(state['ft-host'], '192.168.10.9')
        self.assertNotIn('ft-theme-mode', state)

    def test_sync_requires_idle_disconnected_state_and_revision(self):
        self.window.evaluate_js.return_value = {'active': True, 'unsaved': False}
        with self.assertRaisesRegex(ValueError, 'Finish and log'):
            self.controller.export_sync_file()
        self.window.evaluate_js.return_value = {'active': False, 'unsaved': False}
        self.bridge.state['connected'] = True
        with self.assertRaisesRegex(ValueError, 'Disconnect'):
            self.controller.export_sync_file()
        self.bridge.state['connected'] = False
        self.store.change('ft-shooter-profiles-v1', '[]', expected_revision=0)
        with self.assertRaises(StorageConflict):
            self.controller.apply_sync({'expected_revision': 0, 'updates': {'ft-theme-mode': 'dark'}})

    def test_single_instance_lock_releases_cleanly(self):
        first = InstanceLock(self.temp.name).acquire()
        try:
            with self.assertRaises(RuntimeError):
                InstanceLock(self.temp.name).acquire()
        finally:
            first.release()
        second = InstanceLock(self.temp.name).acquire()
        second.release()


class CloseTests(unittest.TestCase):
    def test_unsaved_cancel_keeps_window_open(self):
        window = Mock()
        window.evaluate_js.return_value = {'unsaved': True, 'active': False}
        window.create_confirmation_dialog.return_value = False
        close = CloseCoordinator(window)
        close.run()
        window.destroy.assert_not_called()
        self.assertFalse(close.allowed)

    def test_confirmed_close_and_idle_close(self):
        for unsaved in (True, False):
            window = Mock()
            window.evaluate_js.return_value = {'unsaved': unsaved}
            window.create_confirmation_dialog.return_value = True
            close = CloseCoordinator(window)
            close.run()
            self.assertTrue(close.allowed)
            window.destroy.assert_called_once()
            self.assertEqual(window.create_confirmation_dialog.call_count, int(unsaved))
            self.assertTrue(close.request())

    def test_first_close_delegates_off_gui_thread_and_repeated_close_waits(self):
        window = Mock()
        close = CloseCoordinator(window)
        with patch('desktop.threading.Thread') as thread:
            self.assertFalse(close.request())
            self.assertFalse(close.request())
            self.assertEqual(thread.call_count, 1)
            thread.return_value.start.assert_called_once()


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = DataStore(self.temp.name)
        self.controller = DesktopController(self.store, bridge, ASSETS)
        self.server = DesktopHTTPServer(self.controller)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, body=None, *, token=True, origin=None, host=None, raw=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        headers = {'Host': host or self.server.host}
        if token:
            headers['X-FT-Session'] = self.server.token
        if origin:
            headers['Origin'] = origin
        if body is not None or raw is not None:
            headers['Content-Type'] = 'application/json'
            connection.request('POST', path, body=raw if raw is not None else json.dumps(body), headers=headers)
        else:
            connection.request('GET', path, headers=headers)
        response = connection.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return result

    def test_http_commit_reopen_and_revision_conflict(self):
        path = '/desktop/store'
        status, raw, _ = self.request(path, dict(key='ft-theme', value='dark', expected_revision=0))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['revision'], 1)
        self.assertEqual(DataStore(self.temp.name).snapshot()['storage']['ft-theme'], 'dark')
        self.assertEqual(self.request(path, dict(key='ft-theme', value='light', expected_revision=0))[0], 409)
        self.assertEqual(self.store.snapshot()['storage']['ft-theme'], 'dark')

    def test_host_origin_token_and_unknown_pages_are_rejected(self):
        for kwargs in ({'token': False}, {'origin': 'https://example.com'}, {'host': 'example.com'}):
            self.assertEqual(self.request('/desktop/info', **kwargs)[0], 403)
        self.assertEqual(self.request('/', token=False)[0], 403)
        self.assertEqual(self.request('/app/not-the-secret/', token=False)[0], 403)
        self.assertEqual(self.request('/unrecognized')[0], 404)

    def test_bootstrap_preserves_strings_without_script_injection(self):
        value = '</script><script>alert("unsafe")</script>\u2028測試'
        self.store.change('ft-text', value, expected_revision=0)
        status, raw, headers = self.request(self.server.app_path, token=False)
        html = raw.decode()
        self.assertEqual(status, 200)
        self.assertNotIn(value, html)
        self.assertNotIn('<!--DESKTOP_BOOTSTRAP-->', html)
        start = html.index('const boot=') + len('const boot=')
        boot = json.JSONDecoder().raw_decode(html[start:])[0]
        self.assertEqual(boot['storage']['ft-text'], value)
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn("connect-src 'self'", headers['Content-Security-Policy'])

    def test_sync_core_and_controls_are_in_the_served_windows_ui(self):
        status, raw, _ = self.request(self.server.app_path, token=False)
        html = raw.decode('utf-8')
        self.assertEqual(status, 200)
        self.assertIn('window.FTPortableSyncCore', html)
        self.assertIn('Sync With Android', html)
        self.assertIn('/desktop/read-sync', html)
        self.assertIn('/desktop/apply-sync', html)

    def test_invalid_body_cannot_mutate_data(self):
        for raw in ('[]', '{broken}', '{"key":"ft-theme","key":"ft-text"}', '{"value":NaN}'):
            self.assertEqual(self.request('/desktop/store', raw=raw)[0], 400)
        self.assertEqual(self.store.snapshot()['storage'], {})

    def test_hardware_routes_use_baseline_handler(self):
        with patch.object(bridge.Handler, 'do_GET') as get:
            # Direct handler test avoids requiring a fake responder to write HTTP bytes.
            from service import DesktopHandler
            handler = DesktopHandler.__new__(DesktopHandler)
            handler.server = self.server
            handler.headers = {'Host': self.server.host, 'X-FT-Session': self.server.token}
            handler.path = '/api/events?after=12'
            handler.do_GET()
            get.assert_called_once()
        with patch.object(bridge.Handler, 'do_POST') as post:
            handler.path = '/api/connect'
            handler.do_POST()
            post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
