from __future__ import annotations
import json
from datetime import datetime

from storage import canonical, strict_json, validate_storage

FORMAT = 'freetarget-portable-sync'
SCHEMA = 1
MAX_SYNC_BYTES = 32 * 1024 * 1024
PROFILE_KEY = 'ft-shooter-profiles-v1'
HISTORY_KEY = 'ft-session-history-v1'
SETTING_KEYS = frozenset({
    'ft-appearance-v1', 'ft-color', 'ft-fade-target-overlays', 'ft-five-prep',
    'ft-five-series', 'ft-five-sighting', 'ft-heatmap-settings-v1',
    'ft-ignore-misses', 'ft-language-v1', 'ft-mean-group', 'ft-page-overrides-v1',
    'ft-pause-on-leave', 'ft-prompt-on-idle-shot', 'ft-regional-format',
    'ft-rule-presets-v1', 'ft-session-formats-v1', 'ft-target-distance',
    'ft-theme-mode', 'ft-voice-enabled', 'ft-voice-language', 'ft-voice-mode',
    'ft-voice-pitch', 'ft-voice-rate', 'ft-voice-volume',
})
SYNC_KEYS = frozenset({PROFILE_KEY, HISTORY_KEY}) | SETTING_KEYS


def _validate_records(profiles, history):
    if not isinstance(profiles, list) or not isinstance(history, list):
        raise ValueError('Sync profiles and sessions must be arrays.')
    names = set()
    for profile in profiles:
        if not isinstance(profile, dict) or not isinstance(profile.get('name'), str) or not profile['name'].strip():
            raise ValueError('A sync file contains an invalid profile.')
        if 'id' in profile and not isinstance(profile['id'], str):
            raise ValueError('A sync file contains a profile with an invalid ID.')
        name = profile['name'].strip().lower()
        if name in names:
            raise ValueError('A sync file contains duplicate profile names.')
        names.add(name)
    for session in history:
        if not isinstance(session, dict) or 'id' in session and not isinstance(session['id'], str):
            raise ValueError('A sync file contains an invalid session.')


def validate_sync_document(document):
    if not isinstance(document, dict) or set(document) != {'format', 'schema', 'created_at', 'source', 'data'}:
        raise ValueError('This is not a supported freETarget sync file.')
    if document.get('format') != FORMAT or type(document.get('schema')) is not int or document['schema'] != SCHEMA:
        raise ValueError('This is not a supported freETarget sync file.')
    if document.get('source') not in {'android', 'windows'}:
        raise ValueError('The sync file has an invalid source.')
    created_at = document.get('created_at')
    if not isinstance(created_at, str) or len(created_at) > 64:
        raise ValueError('The sync file has an invalid timestamp.')
    try:
        datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('The sync file has an invalid timestamp.') from exc

    data = document.get('data')
    if not isinstance(data, dict) or set(data) != {'profiles', 'history', 'settings'}:
        raise ValueError('The sync file data is incomplete.')
    profiles, history, settings = data['profiles'], data['history'], data['settings']
    _validate_records(profiles, history)
    if not isinstance(settings, dict) or not settings.keys() <= SETTING_KEYS:
        raise ValueError('The sync file includes a non-portable setting.')
    storage = {
        PROFILE_KEY: json.dumps(profiles, ensure_ascii=False, separators=(',', ':'), allow_nan=False),
        HISTORY_KEY: json.dumps(history, ensure_ascii=False, separators=(',', ':'), allow_nan=False),
    }
    for key, value in settings.items():
        if value is not None:
            if not isinstance(value, str):
                raise ValueError('A sync setting is invalid.')
            storage[key] = value
    validate_storage(storage)
    if len(canonical(document)) > MAX_SYNC_BYTES:
        raise ValueError('The sync file exceeds 32 MB.')
    return document


def document_from_storage(storage, source):
    if source not in {'android', 'windows'}:
        raise ValueError('Unknown sync source.')
    profiles = strict_json(storage.get(PROFILE_KEY, '[]'))
    history = strict_json(storage.get(HISTORY_KEY, '[]'))
    settings = {key: storage.get(key) for key in sorted(SETTING_KEYS)}
    return validate_sync_document({
        'format': FORMAT,
        'schema': SCHEMA,
        'created_at': datetime.now().astimezone().isoformat(),
        'source': source,
        'data': {'profiles': profiles, 'history': history, 'settings': settings},
    })


def read_sync_file(raw):
    if len(raw) > MAX_SYNC_BYTES:
        raise ValueError('The sync file exceeds 32 MB.')
    document = strict_json(raw.decode('utf-8-sig'))
    return validate_sync_document(document)


def validate_sync_updates(updates):
    if not isinstance(updates, dict) or not updates:
        raise ValueError('The sync merge contains invalid application data.')
    if not updates.keys() <= SYNC_KEYS:
        if any(isinstance(key, str) and key.startswith('ft-') and key not in SYNC_KEYS for key in updates):
            raise ValueError('The sync merge includes a non-portable setting.')
        raise ValueError('The sync merge contains invalid application data.')
    validated = {}
    for key, value in updates.items():
        if value is None:
            if key not in SETTING_KEYS:
                raise ValueError('Sync cannot remove profiles or session history.')
        elif not isinstance(value, str):
            raise ValueError('A sync update is invalid.')
        validated[key] = value
    complete = {
        PROFILE_KEY: '[]',
        HISTORY_KEY: '[]',
        **{key: value for key, value in validated.items() if value is not None},
    }
    validate_storage(complete)
    return validated
