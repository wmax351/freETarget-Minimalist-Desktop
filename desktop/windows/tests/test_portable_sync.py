import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
from portable_sync import document_from_storage, read_sync_file, validate_sync_document, validate_sync_updates


class PortableSyncTests(unittest.TestCase):
    def setUp(self):
        self.storage = {
            'ft-shooter-profiles-v1': json.dumps([{'id': 'p-1', 'name': 'Alex', 'guns': []}]),
            'ft-session-history-v1': json.dumps([{'id': 's-1', 'name': 'Alex'}]),
            'ft-theme-mode': 'dark',
            'ft-host': '192.168.10.9',
        }

    def test_roundtrip_contains_profiles_history_and_only_portable_settings(self):
        document = document_from_storage(self.storage, 'windows')
        parsed = read_sync_file(json.dumps(document, ensure_ascii=False).encode('utf-8'))
        self.assertEqual(parsed['data']['profiles'], [{'id': 'p-1', 'name': 'Alex', 'guns': []}])
        self.assertEqual(parsed['data']['history'], [{'id': 's-1', 'name': 'Alex'}])
        self.assertEqual(parsed['data']['settings']['ft-theme-mode'], 'dark')
        self.assertNotIn('ft-host', parsed['data']['settings'])
        self.assertNotIn('ft-voice-uri', parsed['data']['settings'])

    def test_rejects_unknown_connection_settings_and_duplicate_profile_names(self):
        document = document_from_storage(self.storage, 'windows')
        document['data']['settings']['ft-host'] = 'attacker'
        with self.assertRaisesRegex(ValueError, 'non-portable'):
            validate_sync_document(document)
        document = document_from_storage(self.storage, 'android')
        document['data']['profiles'].append({'id': 'p-2', 'name': 'alex'})
        with self.assertRaisesRegex(ValueError, 'duplicate profile names'):
            validate_sync_document(document)

    def test_update_validation_allows_portable_setting_removal_only(self):
        self.assertEqual(validate_sync_updates({'ft-theme-mode': None}), {'ft-theme-mode': None})
        with self.assertRaisesRegex(ValueError, 'non-portable'):
            validate_sync_updates({'ft-host': '192.168.1.1'})
        with self.assertRaisesRegex(ValueError, 'cannot remove'):
            validate_sync_updates({'ft-session-history-v1': None})

    def test_rejects_duplicate_json_keys_and_unsupported_schema(self):
        with self.assertRaisesRegex(ValueError, 'duplicate keys'):
            read_sync_file(b'{"format":"freetarget-portable-sync","format":"bad"}')
        document = document_from_storage(self.storage, 'windows')
        document['schema'] = 2
        with self.assertRaisesRegex(ValueError, 'supported'):
            validate_sync_document(document)


if __name__ == '__main__':
    unittest.main()
