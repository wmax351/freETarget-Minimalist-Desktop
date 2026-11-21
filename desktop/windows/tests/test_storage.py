import base64
import contextlib
import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
import storage
from storage import DataStore, StorageConflict, read_backup, strict_json


def sample():
    return {
        'ft-shooter-profiles-v1': json.dumps([{'name': 'David — 測試', 'guns': [{'id': 'c55p', 'model': 'C55P'}]}]),
        'ft-session-history-v1': json.dumps([{'mode': 'Five-Shot Standard', 'rules': {'mode': 'Five-Shot Standard', 'seriesSize': 5}, 'shotData': [{'x': -2.5, 'y': 1, 'score': 10}], 'shooter': {'name': 'David'}}]),
        'ft-theme': 'dark',
        'ft-custom-logo-v1': json.dumps({'name': 'Club', 'width': 1, 'height': 1,
            'dataURL': 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nlogo').decode()}),
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = DataStore(self.temp.name)

    def populate(self):
        for key, value in sample().items():
            self.store.change(key, value, expected_revision=self.store.snapshot()['revision'])

    def test_committed_values_survive_reopen_with_history_and_logo(self):
        self.populate()
        self.store.checkpoint()
        state = DataStore(self.temp.name).snapshot()
        self.assertEqual(state, {'revision': 4, 'storage': sample()})
        self.assertEqual(storage.summary(state['storage']), dict(shooters=1, guns=1, sessions=1, preferences=4, has_logo=True))

    def test_dedup_remove_and_stale_revision(self):
        self.store.change('ft-theme', 'dark', expected_revision=0)
        self.assertEqual(self.store.change('ft-theme', 'dark', expected_revision=1)['revision'], 1)
        with self.assertRaises(StorageConflict):
            self.store.change('ft-theme', 'light', expected_revision=0)
        with self.assertRaises(StorageConflict):
            self.store.change('ft-theme', 'light', expected_revision=True)
        self.assertEqual(self.store.snapshot()['storage']['ft-theme'], 'dark')
        self.assertEqual(self.store.change('ft-no-key', remove=True, expected_revision=1)['revision'], 1)
        self.assertEqual(self.store.change('ft-theme', remove=True, expected_revision=1)['revision'], 2)
        self.assertEqual(self.store.snapshot()['storage'], {})

    def test_failed_transaction_rolls_back_values_and_revision(self):
        self.populate()
        before = self.store.snapshot()
        with contextlib.closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("CREATE TRIGGER no_changes BEFORE UPDATE ON meta WHEN NEW.key='revision' BEGIN SELECT RAISE(ABORT, 'disk write failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.change('ft-theme', 'light', expected_revision=4)
        self.assertEqual(self.store.snapshot(), before)
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.restore({'ft-theme': 'light'}, expected_revision=4, confirmed=True)
        self.assertEqual(self.store.snapshot(), before)

    def test_backup_roundtrip_and_before_restore_copy(self):
        self.populate()
        original = self.store.snapshot()
        exported = pathlib.Path(self.temp.name) / 'export.json'
        self.store.export(exported)
        values, source = read_backup(exported.read_bytes())
        self.assertEqual(values, original['storage'])
        self.assertEqual(source['format'], 'freetarget-desktop-backup')
        result = self.store.restore({'ft-theme': 'light'}, expected_revision=4, confirmed=True)
        before = self.store.backups / result['backup_filename']
        self.assertEqual(read_backup(before.read_bytes())[0], original['storage'])
        self.assertEqual(self.store.snapshot(), dict(revision=5, storage={'ft-theme': 'light'}))

    def test_backup_failure_prevents_restore_and_export_keeps_old_copy(self):
        self.populate()
        before = self.store.snapshot()
        with patch.object(storage, 'atomic_write', side_effect=OSError('full')):
            with self.assertRaises(OSError):
                self.store.restore({'ft-theme': 'light'}, expected_revision=4, confirmed=True)
        self.assertEqual(self.store.snapshot(), before)
        target = pathlib.Path(self.temp.name) / 'export.json'
        target.write_bytes(b'old-backup')
        with patch.object(storage.os, 'replace', side_effect=OSError('full')):
            with self.assertRaises(OSError):
                self.store.export(target)
        self.assertEqual(target.read_bytes(), b'old-backup')
        self.assertFalse(list(target.parent.glob('.freetarget-*.tmp')))

    def test_unconfirmed_stale_and_invalid_restore_never_changes_data(self):
        self.populate()
        before = self.store.snapshot()
        for kwargs in ({'expected_revision': 4, 'confirmed': False}, {'expected_revision': 3, 'confirmed': True}):
            with self.assertRaises(ValueError):
                self.store.restore({}, **kwargs)
        for invalid in ({'other-app': 'x'}, {'ft-theme': 42}, {'ft-session-history-v1': '[{} ,1]'}, {'ft-session-history-v1': '[{"shotData":[]}]'}, {'ft-custom-logo-v1': '{}'}):
            with self.assertRaises(ValueError):
                self.store.restore(invalid, expected_revision=4, confirmed=True)
        self.assertEqual(self.store.snapshot(), before)

    def test_browser_export_imports_indexeddb_logo_and_preserves_raw_strings(self):
        values = sample()
        logo = json.loads(values.pop('ft-custom-logo-v1'))
        doc = {'format': 'freetarget-browser-export', 'schema': 1, 'storage': values, 'logo': logo}
        parsed, _ = read_backup(json.dumps(doc).encode())
        self.assertEqual(json.loads(parsed['ft-custom-logo-v1']), logo)
        for key, value in values.items():
            self.assertEqual(parsed[key], value)
        self.store.restore(parsed, expected_revision=0, confirmed=True)
        self.assertEqual(storage.summary(self.store.snapshot()['storage'])['sessions'], 1)

    def test_rejects_bad_checksum_duplicate_json_nan_and_active_logo(self):
        self.populate()
        doc = json.loads(self.store.backup_bytes())
        doc['storage']['ft-theme'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'integrity'):
            read_backup(json.dumps(doc).encode())
        for bad in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError):
                strict_json(bad)
        for body in ('<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>', '<svg onload="alert(1)"/>', '<svg><image href="https://example.com/a"/></svg>'):
            logo = {'name': 'bad', 'width': 1, 'height': 1, 'dataURL': 'data:image/svg+xml;base64,' + base64.b64encode(body.encode()).decode()}
            with self.assertRaises(ValueError):
                storage.validate_logo(logo)

    def test_automatic_backup_retention_and_daily_dedup(self):
        self.populate()
        first = self.store.automatic_backup(daily=True)
        self.assertTrue(first.is_file())
        self.assertIsNone(self.store.automatic_backup(daily=True))
        manual = self.store.backups / 'my-own-copy.json'
        manual.write_text('preserve')
        for _ in range(34):
            self.store.automatic_backup()
        self.assertEqual(len(list(self.store.backups.glob('auto-*.json'))), 30)
        self.assertEqual(manual.read_text(), 'preserve')

    def test_repeated_clock_ticks_do_not_overwrite_automatic_backups(self):
        self.populate()
        frozen = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
        with patch.object(storage, 'datetime') as clock:
            clock.now.return_value = frozen
            first = self.store.automatic_backup(daily=True)
            self.assertIsNone(self.store.automatic_backup(daily=True))
            second = self.store.automatic_backup()
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_file())
            self.assertTrue(second.is_file())
            for _ in range(34):
                self.store.automatic_backup()
        self.assertEqual(len(list(self.store.backups.glob('auto-*.json'))), 30)

    def test_unknown_schema_is_preserved(self):
        with contextlib.closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
        with self.assertRaisesRegex(ValueError, 'not changed'):
            DataStore(self.temp.name)
        with contextlib.closing(sqlite3.connect(self.store.path)) as db, db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0], '99')


if __name__ == '__main__':
    unittest.main()
