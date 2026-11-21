from __future__ import annotations
import pathlib
import os
import json
import uuid
import sys
import subprocess
import secrets
import threading
import time
import webbrowser
from datetime import datetime
from storage import MAX_BACKUP, atomic_write, read_backup, strict_json, summary, validate_storage
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
        self._sync_stage = None

    def info(self):
        state = self.store.snapshot()
        return dict(app_version=APP_VERSION, ui_base_version=BASELINE_VERSION, data_folder=str(self.store.directory),
                    database=str(self.store.path), revision=state['revision'], summary=summary(state['storage']),
                    backup_warning=self.backup_warning)

    def _choose(self, save=False):
        if not self.window or not self.webview:
            raise ValueError('The desktop window is not ready.')
        if not self._dialog_lock.acquire(blocking=False):
            raise ValueError('Another file dialog is already open.')
        try:
            if save:
                result = self.window.create_file_dialog(self.webview.FileDialog.SAVE,
                    save_filename='freETarget-backup-' + datetime.now().strftime('%Y-%m-%d-%H%M%S') + '.json',
                    file_types=('freETarget Backup (*.json)',))
            else:
                result = self.window.create_file_dialog(self.webview.FileDialog.OPEN,
                    allow_multiple=False, file_types=('freETarget Backup (*.json)',))
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

    def open_data_folder(self):
        if sys.platform == 'darwin':
            subprocess.run(['open', str(self.store.directory)], check=True)
        elif sys.platform == 'win32':
            os.startfile(str(self.store.directory))
        else:
            raise ValueError('Open Data Folder is available in the native desktop app.')
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

    def _icloud_account(self):
        if sys.platform != 'darwin':
            raise ValueError('iCloud sync is available on Apple devices.')
        from Foundation import NSFileManager, NSKeyedArchiver
        manager = NSFileManager.defaultManager()
        identity = manager.ubiquityIdentityToken()
        if identity is None:
            raise ValueError('iCloud Drive is unavailable. Check iCloud settings and app signing.')
        return bytes(NSKeyedArchiver.archivedDataWithRootObject_(identity))

    def apple_sync_read(self, obj):
        self._assert_idle()
        from Foundation import NSFileManager, NSURL
        if not self._dialog_lock.acquire(blocking=False):
            raise ValueError('Another data operation is already open.')
        try:
            self._sync_stage = None
            account = self._icloud_account()
            account_file = self.store.directory / 'apple-sync-account'
            needs_confirmation = not account_file.exists() or account_file.read_bytes() != account
            if obj.get('automatic') is True and needs_confirmation:
                raise ValueError('Tap Sync Now to connect this device to the current iCloud account.')
            manager = NSFileManager.defaultManager()
            container = manager.URLForUbiquityContainerIdentifier_(None)
            if container is None:
                raise ValueError('The shared iCloud container is unavailable. Check app signing and iCloud Drive.')
            folder = pathlib.Path(str(container.path())) / 'Documents' / 'freETarget Sync'
            folder.mkdir(parents=True, exist_ok=True)
            identity = self.store.directory / 'apple-sync-device-id'
            if not identity.exists():
                atomic_write(identity, str(uuid.uuid4()).encode('ascii'))
            device = str(uuid.UUID(identity.read_text(encoding='ascii')))
            replicas = []
            size = 0
            for path in sorted(folder.iterdir()):
                if path.name.startswith('.freetarget-sync-') and path.name.endswith('.json.icloud'):
                    visible = folder / path.name[1:-len('.icloud')]
                    ok, error = manager.startDownloadingUbiquitousItemAtURL_error_(NSURL.fileURLWithPath_(str(visible)), None)
                    if not ok:
                        raise ValueError(str(error) if error else 'Could not download the iCloud sync file.')
                    raise ValueError('iCloud is downloading sync files. Try again shortly.')
                if not path.match('freetarget-sync-*.json'):
                    continue
                if path.is_symlink() or not path.is_file():
                    raise ValueError('Invalid sync file.')
                size += path.stat().st_size
                if size > MAX_BACKUP:
                    raise ValueError('The sync folder exceeds 128 MB.')
                file = strict_json(path.read_bytes())
                if not isinstance(file, dict) or path.name != 'freetarget-sync-' + str(file.get('device')) + '.json':
                    raise ValueError('The folder contains an invalid freETarget sync file.')
                replicas.append(file)
            if self._icloud_account() != account:
                raise ValueError('The iCloud account changed. Tap Sync Now again.')
            token = secrets.token_urlsafe(24)
            self._sync_stage = (token, folder, device, account, time.monotonic() + 600)
            return dict(token=token, device=device, replicas=replicas, needsConfirmation=needs_confirmation)
        finally:
            self._dialog_lock.release()

    def apple_sync_apply(self, obj):
        self._assert_idle()
        with self._stage_lock, self.bridge.lock, self.store._lock:
            if self.bridge.state['connected'] or self.bridge.state['connecting']:
                raise ValueError('Disconnect the target before syncing.')
            stage, self._sync_stage = self._sync_stage, None
            if not stage or obj.get('token') != stage[0] or time.monotonic() > stage[4]:
                raise ValueError('Tap Sync Now again.')
            _, folder, device, account, _ = stage
            if self._icloud_account() != account:
                raise ValueError('The iCloud account changed. Tap Sync Now again.')
            state = self.store.snapshot()
            if obj.get('expected_revision') != state['revision']:
                raise ValueError('Local data changed. Sync again.')
            values = obj.get('values')
            keys = {'ft-shooter-profiles-v1', 'ft-session-history-v1', 'ft-apple-sync-baseline-v1'}
            replica = obj.get('replica')
            if type(values) is not dict or values.keys() != keys or type(replica) is not dict or replica.get('device') != device:
                raise ValueError('Invalid sync data.')
            merged = validate_storage({**state['storage'], **values})
            if obj.get('publish') is True:
                raw = json.dumps(replica, ensure_ascii=False, allow_nan=False).encode('utf-8')
                if len(raw) > MAX_BACKUP:
                    raise ValueError('The sync file exceeds 128 MB.')
                atomic_write(folder / ('freetarget-sync-' + device + '.json'), raw)
            result = self.store.restore(merged, expected_revision=state['revision'], confirmed=True)
            if not (self.store.directory / 'apple-sync-account').exists() or (self.store.directory / 'apple-sync-account').read_bytes() != account:
                atomic_write(self.store.directory / 'apple-sync-account', account)
            return result

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
