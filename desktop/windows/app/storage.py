"""Transactional local preferences/records, portable backups and bounded restore."""
from __future__ import annotations
import base64
import binascii
import contextlib
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import tempfile
import threading
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from version import APP_VERSION, BASELINE_VERSION, SCHEMA_VERSION

MAX_BACKUP = 128 * 1024 * 1024
MAX_VALUE = 64 * 1024 * 1024
KEY_PATTERN = re.compile(r'ft-[A-Za-z0-9][A-Za-z0-9_.:-]{0,126}\Z')

class StorageConflict(ValueError):
    pass


def canonical(storage):
    return json.dumps(storage, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def strict_json(data):
    def reject(value):
        raise ValueError('Backup contains an invalid JSON number: ' + value)
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError('Backup contains duplicate keys.')
            result[key] = value
        return result
    return json.loads(data, parse_constant=reject, object_pairs_hook=pairs)


def validate_logo(logo):
    if not isinstance(logo, dict) or not isinstance(logo.get('dataURL'), str):
        raise ValueError('The custom logo is invalid.')
    match = re.fullmatch(r'data:image/(png|webp|svg\+xml);base64,([A-Za-z0-9+/=\r\n]+)', logo['dataURL'])
    if not match:
        raise ValueError('The logo must be a PNG, WebP or self-contained SVG.')
    try:
        raw = base64.b64decode(match[2], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError('The logo contains invalid image data.') from exc
    if not raw or len(raw) > 2 * 1024 * 1024:
        raise ValueError('The custom logo exceeds 2 MB or is empty.')
    kind = match[1]
    if kind == 'png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('The logo PNG header is invalid.')
    if kind == 'webp' and not (raw.startswith(b'RIFF') and raw[8:12] == b'WEBP'):
        raise ValueError('The logo WebP header is invalid.')
    if kind == 'svg+xml':
        text = raw.decode('utf-8-sig')
        if re.search(r'<!DOCTYPE|<!ENTITY|@import', text, re.I):
            raise ValueError('The logo SVG must be self-contained.')
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise ValueError('The logo SVG is invalid.') from exc
        if root.tag.split('}')[-1].lower() != 'svg':
            raise ValueError('The logo does not contain an SVG root.')
        for node in root.iter():
            if node.tag.split('}')[-1].lower() in {'script', 'foreignobject', 'iframe', 'object', 'embed', 'audio', 'video'}:
                raise ValueError('Active content is not allowed in a logo.')
            for name, value in node.attrib.items():
                name = name.split('}')[-1].lower()
                if name.startswith('on') or name in {'href', 'src'} and not (value.startswith('#') or re.match(r'data:image/(png|jpeg|webp);base64,', value)):
                    raise ValueError('The logo SVG contains active or external resources.')
        for item in re.finditer(r'url\(\s*([\'"]?)(.*?)\1\s*\)', text, re.I):
            if not item[2].strip().startswith('#'):
                raise ValueError('The logo SVG contains an external resource.')
    for field in ('width', 'height'):
        if isinstance(logo.get(field), bool) or not isinstance(logo.get(field), int) or not 0 < logo[field] <= 100000:
            raise ValueError('The custom logo dimensions are invalid.')
    if not isinstance(logo.get('name'), str) or len(logo['name']) > 1024:
        raise ValueError('The custom logo name is invalid.')
    return logo


def validate_entry(key, value):
    if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
        raise ValueError('Unrecognized application data key.')
    if not isinstance(value, str) or len(value.encode('utf-8')) > MAX_VALUE:
        raise ValueError('An application data value is invalid or too large.')
    # Preserve raw JSON strings for compatibility with historical UI versions.
    expected = {
        'ft-shooter-profiles-v1': list, 'ft-session-history-v1': list,
        'ft-demo-session-history-v1': list,
        'ft-shooter-names': list, 'ft-session-formats-v1': dict,
        'ft-rule-presets-v1': dict, 'ft-page-overrides-v1': dict,
        'ft-appearance-v1': dict, 'ft-last-guns-v1': dict,
        'ft-last-successful-connection': dict, 'ft-custom-logo-v1': dict,
        'ft-custom-logo-modes-v1': dict,
    }
    if key in expected:
        parsed = strict_json(value)
        if not isinstance(parsed, expected[key]):
            raise ValueError('Invalid data structure for ' + key)
        if key in ('ft-session-history-v1', 'ft-demo-session-history-v1'):
            for item in parsed:
                if not isinstance(item, dict):
                    raise ValueError('A saved session is not a valid record.')
                if item.get('rules') is not None and not isinstance(item['rules'], dict):
                    raise ValueError('A saved session has invalid rules.')
                if 'shotData' in item:
                    if not isinstance(item['shotData'], list) or any(not isinstance(shot, dict) for shot in item['shotData']):
                        raise ValueError('A saved session has invalid shot data.')
                    if not isinstance(item.get('mode'), str) or not isinstance((item.get('rules') or {}).get('mode'), str):
                        raise ValueError('An individual-shot session is missing its saved session rules.')
                if item.get('shooter') is not None and not isinstance(item['shooter'], dict):
                    raise ValueError('A saved session has invalid shooter data.')
        if key == 'ft-shooter-profiles-v1':
            if any(not isinstance(p, dict) or not isinstance(p.get('name'), str) or 'guns' in p and not isinstance(p['guns'], list) for p in parsed):
                raise ValueError('A shooter profile is invalid.')
        if key == 'ft-session-formats-v1' and not isinstance(parsed.get('entries'), list):
            raise ValueError('The saved session format catalog is invalid.')
        if key == 'ft-custom-logo-v1':
            validate_logo(parsed)
        if key == 'ft-custom-logo-modes-v1':
            if set(parsed) != {'light', 'dark'}:
                raise ValueError('Custom logos must contain light and dark modes.')
            for mode in ('light', 'dark'):
                if parsed[mode] is not None:
                    validate_logo(parsed[mode])
    return value


def validate_storage(storage):
    if not isinstance(storage, dict) or len(storage) > 3000:
        raise ValueError('The backup must contain an application storage object.')
    for key, value in storage.items():
        validate_entry(key, value)
    if len(canonical(storage)) > MAX_BACKUP:
        raise ValueError('The backup exceeds 128 MB.')
    return dict(storage)


def read_backup(raw):
    if len(raw) > MAX_BACKUP:
        raise ValueError('The backup exceeds 128 MB.')
    doc = strict_json(raw.decode('utf-8-sig'))
    if not isinstance(doc, dict) or doc.get('format') not in {'freetarget-desktop-backup', 'freetarget-browser-export'} or type(doc.get('schema')) is not int or doc['schema'] != 1:
        raise ValueError('This is not a supported freETarget backup/export (schema 1).')
    storage = validate_storage(doc.get('storage'))
    if doc.get('checksum_sha256') and doc['checksum_sha256'] != hashlib.sha256(canonical(storage)).hexdigest():
        raise ValueError('Backup integrity check failed. Choose another copy.')
    # IndexedDB is authoritative for the older web app's logo, when present.
    if doc.get('logo') is not None:
        storage['ft-custom-logo-v1'] = json.dumps(validate_logo(doc['logo']), ensure_ascii=False, separators=(',', ':'))
    return validate_storage(storage), {key: doc.get(key) for key in ('format', 'created_at', 'app_version', 'ui_base_version')}


def summary(storage):
    profiles = strict_json(storage.get('ft-shooter-profiles-v1', '[]'))
    sessions = strict_json(storage.get('ft-session-history-v1', '[]'))
    modern_logo = strict_json(storage['ft-custom-logo-modes-v1']) if 'ft-custom-logo-modes-v1' in storage else None
    has_logo = any(modern_logo.get(mode) for mode in ('light', 'dark')) if isinstance(modern_logo, dict) else 'ft-custom-logo-v1' in storage
    return dict(shooters=len(profiles), guns=sum(len(p.get('guns', [])) if 'guns' in p else int(any(p.get(k) for k in ('make', 'model', 'caliber', 'nickname'))) for p in profiles),
                sessions=len(sessions), preferences=len(storage), has_logo=has_logo)


def atomic_write(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.freetarget-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


class DataStore:
    def __init__(self, data_dir):
        self.directory = pathlib.Path(data_dir)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'freetarget.sqlite3'
        self.backups = self.directory / 'backups'
        self.backups.mkdir(exist_ok=True)
        self._lock = threading.RLock()
        with self._connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            check = db.execute('PRAGMA quick_check').fetchone()[0]
            if check != 'ok':
                raise ValueError('The local database failed its integrity check. It was not reset.')
            db.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row and row[0] != str(SCHEMA_VERSION):
                raise ValueError('This data folder belongs to a different database version. It was not changed.')
            db.execute('CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
            db.execute("INSERT OR IGNORE INTO meta VALUES('revision', '0')")

    @contextlib.contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA busy_timeout=10000')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _revision(db):
        return int(db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0])

    def snapshot(self):
        with self._lock, self._connect() as db:
            db.execute('BEGIN')
            revision = self._revision(db)
            values = dict(db.execute('SELECT key,value FROM kv'))
            return dict(revision=revision, storage=values)

    def change(self, key, value=None, *, remove=False, expected_revision):
        if remove:
            if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
                raise ValueError('Invalid application data key.')
        else:
            validate_entry(key, value)
        with self._lock, self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            revision = self._revision(db)
            if type(expected_revision) is not int or expected_revision != revision:
                raise StorageConflict('Local data changed. Reload the app before making more changes.')
            old = db.execute('SELECT value FROM kv WHERE key=?', (key,)).fetchone()
            if remove and not old or not remove and old and old[0] == value:
                return dict(revision=revision)
            if remove:
                db.execute('DELETE FROM kv WHERE key=?', (key,))
            else:
                db.execute('INSERT INTO kv VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at', (key, value, datetime.now(timezone.utc).isoformat()))
            revision += 1
            db.execute("UPDATE meta SET value=? WHERE key='revision'", (str(revision),))
            return dict(revision=revision)

    def backup_bytes(self, snapshot=None):
        state = snapshot or self.snapshot()
        values = state['storage']
        return json.dumps(dict(format='freetarget-desktop-backup', schema=1, app_version=APP_VERSION, ui_base_version=BASELINE_VERSION,
                               created_at=datetime.now(timezone.utc).isoformat(), storage=values,
                               checksum_sha256=hashlib.sha256(canonical(values)).hexdigest()), ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')

    def export(self, path):
        atomic_write(path, self.backup_bytes())

    def automatic_backup(self, prefix='auto', daily=False):
        with self._lock:
            state = self.snapshot()
            if not state['storage']:
                return None
            today = datetime.now(timezone.utc).strftime('%Y%m%d')
            if daily and any(self.backups.glob('auto-' + today + '-*.json')):
                return None
            stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
            # Windows clock ticks can repeat across rapid writes. Never reuse
            # a destination name, since atomic_write replaces existing files.
            path = self.backups / (prefix + '-' + stamp + '-' + uuid.uuid4().hex + '.json')
            atomic_write(path, self.backup_bytes(state))
            self._prune_backups()
            return path

    def _prune_backups(self):
        paths = [p for pattern in ('auto-*.json', 'before-restore-*.json') for p in self.backups.glob(pattern)]
        for old in sorted(paths, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)[30:]:
            old.unlink()

    def restore(self, storage, *, expected_revision, confirmed):
        values = validate_storage(storage)
        if confirmed is not True:
            raise ValueError('Confirm the preview before replacing desktop data.')
        with self._lock, self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            revision = self._revision(db)
            if type(expected_revision) is not int or revision != expected_revision:
                raise StorageConflict('Local data changed since the preview. Preview the backup again.')
            current = dict(db.execute('SELECT key,value FROM kv'))
            backup = None
            if current:
                stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
                backup = self.backups / ('before-restore-' + stamp + '-' + uuid.uuid4().hex + '.json')
                atomic_write(backup, self.backup_bytes(dict(storage=current, revision=revision)))
            db.execute('DELETE FROM kv')
            now = datetime.now(timezone.utc).isoformat()
            db.executemany('INSERT INTO kv VALUES(?,?,?)', [(key, value, now) for key, value in values.items()])
            revision += 1
            db.execute("UPDATE meta SET value=? WHERE key='revision'", (str(revision),))
        with contextlib.suppress(OSError):
            self._prune_backups()
        return dict(revision=revision, backup_filename=backup.name if backup else None, summary=summary(values))

    def checkpoint(self):
        with self._lock, self._connect() as db:
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
