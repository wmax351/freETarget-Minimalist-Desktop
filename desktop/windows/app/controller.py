from __future__ import annotations
import pathlib
import os
import sys
import json
import secrets
import threading
import time
import webbrowser
from datetime import datetime
from storage import MAX_BACKUP, StorageConflict, atomic_write, read_backup, summary
from portable_sync import MAX_SYNC_BYTES, document_from_storage, read_sync_file, validate_sync_updates
from version import APP_VERSION, BASELINE_VERSION


class DesktopController:
    def __init__(self, store, bridge, assets):
        self.store, self.bridge, self.assets = store, bridge, pathlib.Path(assets)
        self.window = None
        self.webview = None
        self._staged = None
        self._stage_lock = threading.RLock()
        self.exporter = None
        self.backup_warning = None
        self._dialog_lock = threading.Lock()

    def info(self):
        state = self.store.snapshot()
        return dict(app_version=APP_VERSION, ui_base_version=BASELINE_VERSION, data_folder=str(self.store.directory),
                    database=str(self.store.path), revision=state['revision'], summary=summary(state['storage']),
                    backup_warning=self.backup_warning)

    def _choose(self, save=False, *, file_kind='Backup'):
        if not self.window or not self.webview:
            raise ValueError('The desktop window is not ready.')
        if not self._dialog_lock.acquire(blocking=False):
            raise ValueError('Another file dialog is already open.')
        try:
            filename = 'freETarget-' + file_kind.lower() + '-' + datetime.now().strftime('%Y-%m-%d-%H%M%S') + '.json'
            if save:
                result = self.window.create_file_dialog(self.webview.FileDialog.SAVE,
                    save_filename=filename, file_types=('freETarget ' + file_kind + ' (*.json)',))
            else:
                result = self.window.create_file_dialog(self.webview.FileDialog.OPEN,
                    allow_multiple=False, file_types=('freETarget ' + file_kind + ' (*.json)',))
            if not result:
                return None
            return pathlib.Path(result[0] if isinstance(result, (list, tuple)) else result)
        finally:
            self._dialog_lock.release()

    def export_backup(self):
        path = self._choose(save=True)
        if path is None:
            return dict(cancelled=True)
        if path.suffix.lower() != '.json':
            path = path.with_name(path.name + '.json')
        # A chosen path must never replace the active DB or its WAL/lock files.
        if path.resolve() in {self.store.path.resolve(), pathlib.Path(str(self.store.path) + '-wal').resolve(), pathlib.Path(str(self.store.path) + '-shm').resolve()}:
            raise ValueError('Choose a separate JSON backup file.')
        self.store.export(path)
        return dict(saved=True, filename=path.name)

    def _assert_idle(self):
        if self.window:
            state = self.window.evaluate_js('typeof window.FTDesktopSessionState === "function" ? window.FTDesktopSessionState() : null')
            if not isinstance(state, dict) or state.get('active') or state.get('unsaved'):
                raise ValueError('Finish and log or discard the current session before restoring data.')

    def _assert_disconnected(self):
        with self.bridge.lock:
            if self.bridge.state['connected'] or self.bridge.state['connecting']:
                raise ValueError('Disconnect the target before syncing.')

    def open_data_folder(self):
        if sys.platform != 'win32':
            raise ValueError('Open Data Folder is available in the Windows desktop app.')
        os.startfile(str(self.store.directory))
        return dict(opened=True)

    def preview_backup(self):
        self._assert_idle()
        with self.bridge.lock:
            if self.bridge.state['connected'] or self.bridge.state['connecting']:
                raise ValueError('Disconnect the target before restoring or migrating data.')
        path = self._choose()
        if path is None:
            return dict(cancelled=True)
        if path.stat().st_size > MAX_BACKUP:
            raise ValueError('The backup exceeds 128 MB.')
        with path.open('rb') as stream:
            raw = stream.read(MAX_BACKUP + 1)
        values, source = read_backup(raw)
        current = self.store.snapshot()
        stage = dict(id=secrets.token_urlsafe(24), storage=values, expires=time.monotonic() + 600,
                     revision=current['revision'])
        with self._stage_lock:
            self._staged = stage
        return dict(import_id=stage['id'], filename=path.name, incoming=summary(values), current=summary(current['storage']),
                    expected_revision=stage['revision'], source=source)

    def restore_backup(self, obj):
        self._assert_idle()
        with self._stage_lock:
            stage = self._staged
            if not stage or not secrets.compare_digest(str(obj.get('import_id', '')).encode('utf-8'), stage['id'].encode('ascii')) or time.monotonic() > stage['expires']:
                raise ValueError('The preview expired. Choose and preview the backup again.')
            if obj.get('expected_revision') != stage['revision']:
                raise ValueError('The restore request does not match the preview.')
            with self.bridge.lock:
                if self.bridge.state['connected'] or self.bridge.state['connecting']:
                    raise ValueError('Disconnect the target before restoring data.')
                result = self.store.restore(stage['storage'], expected_revision=stage['revision'], confirmed=obj.get('confirmed') is True)
            self._staged = None
            return result

    def export_sync_file(self):
        self._assert_idle()
        self._assert_disconnected()
        path = self._choose(save=True, file_kind='Sync')
        if path is None:
            return dict(cancelled=True)
        if path.suffix.lower() != '.json':
            path = path.with_name(path.name + '.json')
        if path.resolve() in {self.store.path.resolve(),
                pathlib.Path(str(self.store.path) + '-wal').resolve(),
                pathlib.Path(str(self.store.path) + '-shm').resolve()}:
            raise ValueError('Choose a separate sync file.')
        state = self.store.snapshot()
        document = document_from_storage(state['storage'], 'windows')
        raw = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
        if len(raw) > MAX_SYNC_BYTES:
            raise ValueError('The sync file exceeds 32 MB.')
        atomic_write(path, raw)
        return dict(saved=True, filename=path.name, summary=summary(state['storage']))

    def read_sync_file(self):
        self._assert_idle()
        self._assert_disconnected()
        path = self._choose(file_kind='Sync')
        if path is None:
            return dict(cancelled=True)
        if path.is_symlink() or not path.is_file():
            raise ValueError('Choose a regular freETarget sync file.')
        if path.stat().st_size > MAX_SYNC_BYTES:
            raise ValueError('The sync file exceeds 32 MB.')
        with path.open('rb') as stream:
            document = read_sync_file(stream.read(MAX_SYNC_BYTES + 1))
        self._assert_idle()
        self._assert_disconnected()
        state = self.store.snapshot()
        return dict(document=document, filename=path.name, expected_revision=state['revision'],
                    current=summary(state['storage']))

    def apply_sync(self, obj):
        self._assert_idle()
        updates = validate_sync_updates(obj.get('updates'))
        with self.bridge.lock:
            if self.bridge.state['connected'] or self.bridge.state['connecting']:
                raise ValueError('Disconnect the target before syncing.')
            state = self.store.snapshot()
            if type(obj.get('expected_revision')) is not int or obj['expected_revision'] != state['revision']:
                raise StorageConflict('Local data changed during sync. Import the file again.')
            merged = dict(state['storage'])
            for key, value in updates.items():
                if value is None:
                    merged.pop(key, None)
                else:
                    merged[key] = value
            return self.store.restore(merged, expected_revision=state['revision'], confirmed=True)

    def start_browser_exporter(self):
        if self.exporter is None:
            from migration_exporter import create_export_server
            try:
                self.exporter = create_export_server(self.assets / 'browser_export.html', 8765)
            except OSError as exc:
                raise ValueError('Port 8765 is in use. Stop the old bridge/export helper first, then try again.') from exc
            threading.Thread(target=self.exporter.serve_forever, daemon=True).start()
        url = 'http://127.0.0.1:8765/'
        webbrowser.open(url)
        return dict(url=url, message='Use this address in the original browser and browser profile. Export there, then restore its JSON file here.')

    def stop(self):
        if self.exporter:
            self.exporter.shutdown()
            self.exporter.server_close()
            self.exporter = None
