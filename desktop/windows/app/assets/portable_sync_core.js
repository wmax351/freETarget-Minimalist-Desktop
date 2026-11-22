(function (root, factory) {
    'use strict';
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.FTPortableSyncCore = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
    'use strict';

    const FORMAT = 'freetarget-portable-sync';
    const SCHEMA = 1;
    const PROFILE_KEY = 'ft-shooter-profiles-v1';
    const HISTORY_KEY = 'ft-session-history-v1';
    const SETTINGS = [
        'ft-appearance-v1', 'ft-color', 'ft-fade-target-overlays', 'ft-five-prep',
        'ft-five-series', 'ft-five-sighting', 'ft-heatmap-settings-v1',
        'ft-ignore-misses', 'ft-language-v1', 'ft-mean-group', 'ft-page-overrides-v1',
        'ft-pause-on-leave', 'ft-prompt-on-idle-shot', 'ft-regional-format',
        'ft-rule-presets-v1', 'ft-session-formats-v1', 'ft-target-distance',
        'ft-theme-mode', 'ft-voice-enabled', 'ft-voice-language', 'ft-voice-mode',
        'ft-voice-pitch', 'ft-voice-rate', 'ft-voice-volume'
    ];
    const SETTINGS_SET = new Set(SETTINGS);
    const SETTING_LABELS = {
        'ft-appearance-v1': 'Appearance',
        'ft-color': 'Color',
        'ft-fade-target-overlays': 'Target overlay fade',
        'ft-five-prep': 'Five-shot preparation',
        'ft-five-series': 'Five-shot series',
        'ft-five-sighting': 'Five-shot sighting',
        'ft-heatmap-settings-v1': 'Heatmap',
        'ft-ignore-misses': 'Ignore misses',
        'ft-language-v1': 'Language',
        'ft-mean-group': 'Mean group',
        'ft-page-overrides-v1': 'Page appearance',
        'ft-pause-on-leave': 'Pause session when leaving live scoring',
        'ft-prompt-on-idle-shot': 'Prompt to start a session',
        'ft-regional-format': 'Regional format',
        'ft-rule-presets-v1': 'Competition rules',
        'ft-session-formats-v1': 'Session formats',
        'ft-target-distance': 'Target distance',
        'ft-theme-mode': 'Theme',
        'ft-voice-enabled': 'Voice scoring',
        'ft-voice-language': 'Voice language',
        'ft-voice-mode': 'Voice mode',
        'ft-voice-pitch': 'Voice pitch',
        'ft-voice-rate': 'Voice rate',
        'ft-voice-volume': 'Voice volume'
    };

    function canonical(value) {
        if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
        if (value && typeof value === 'object') {
            return '{' + Object.keys(value).sort().map(key =>
                JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
        }
        return JSON.stringify(value);
    }

    function hasOwn(value, key) {
        return Object.prototype.hasOwnProperty.call(value, key);
    }

    function hasExactKeys(value, keys) {
        const actual = Object.keys(value);
        return actual.length === keys.length && keys.every(key => hasOwn(value, key));
    }

    function hash(text) {
        let first = 2166136261, second = 2246822519;
        for (let index = 0; index < text.length; index++) {
            first = Math.imul(first ^ text.charCodeAt(index), 16777619) >>> 0;
            second = Math.imul(second ^ text.charCodeAt(index), 3266489917) >>> 0;
        }
        return ('00000000' + first.toString(16)).slice(-8) +
            ('00000000' + second.toString(16)).slice(-8);
    }

    function object(value, label) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            throw Error(label + ' must be an object.');
        }
        return value;
    }

    function records(value, label) {
        if (!Array.isArray(value)) throw Error(label + ' must be an array.');
        for (const item of value) object(item, label + ' record');
        return value;
    }

    function rowId(value) {
        return typeof value.id === 'string' && value.id ? value.id : 'legacy:' + hash(canonical(value));
    }

    function parseLocal(storage, key, label) {
        let value;
        try {
            value = JSON.parse(storage.getItem(key) || '[]');
        } catch {
            throw Error('Local ' + label + ' data is invalid. No data was changed.');
        }
        return records(value, 'Local ' + label);
    }

    function validateRecordArrays(profiles, history) {
        const names = new Set();
        for (const profile of records(profiles, 'Profiles')) {
            if (typeof profile.name !== 'string' || !profile.name.trim()) {
                throw Error('A sync file contains a profile without a name.');
            }
            if (profile.id !== undefined && typeof profile.id !== 'string') {
                throw Error('A sync file contains a profile with an invalid ID.');
            }
            if (profile.guns !== undefined && !Array.isArray(profile.guns)) {
                throw Error('A sync file contains invalid guns.');
            }
            const name = profile.name.trim().toLowerCase();
            if (names.has(name)) throw Error('A sync file contains duplicate profile names.');
            names.add(name);
        }
        for (const session of records(history, 'Sessions')) {
            if (session.id !== undefined && typeof session.id !== 'string') {
                throw Error('A sync file contains a session with an invalid ID.');
            }
            if (session.rules !== undefined && session.rules !== null &&
                    (typeof session.rules !== 'object' || Array.isArray(session.rules))) {
                throw Error('A sync file contains invalid session rules.');
            }
            if (session.shotData !== undefined &&
                    (!Array.isArray(session.shotData) || session.shotData.some(shot => !shot || typeof shot !== 'object' || Array.isArray(shot)))) {
                throw Error('A sync file contains invalid shot data.');
            }
            if (session.shooter !== undefined && session.shooter !== null &&
                    (!session.shooter || typeof session.shooter !== 'object' || Array.isArray(session.shooter))) {
                throw Error('A sync file contains invalid shooter data.');
            }
        }
    }

    function validateSettings(settings) {
        object(settings, 'Sync settings');
        for (const [key, value] of Object.entries(settings)) {
            if (!SETTINGS_SET.has(key)) throw Error('The sync file includes a non-portable setting.');
            if (value !== null && typeof value !== 'string') throw Error('A sync setting is invalid.');
            if (typeof value !== 'string') continue;
            if (['ft-appearance-v1', 'ft-heatmap-settings-v1', 'ft-page-overrides-v1',
                    'ft-rule-presets-v1', 'ft-session-formats-v1'].includes(key)) {
                let parsed;
                try {
                    parsed = JSON.parse(value);
                } catch {
                    throw Error('The sync file contains invalid ' + SETTING_LABELS[key] + ' settings.');
                }
                if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
                    throw Error('The sync file contains invalid ' + SETTING_LABELS[key] + ' settings.');
                }
                if (key === 'ft-session-formats-v1' && !Array.isArray(parsed.entries)) {
                    throw Error('The sync file contains an invalid session format catalog.');
                }
            }
        }
        return settings;
    }

    function validateDocument(document) {
        object(document, 'Sync file');
        if (!hasExactKeys(document, ['format', 'schema', 'created_at', 'source', 'data']) ||
                document.format !== FORMAT || document.schema !== SCHEMA ||
                !['android', 'windows'].includes(document.source) ||
                typeof document.created_at !== 'string' || document.created_at.length > 64 ||
                !Number.isFinite(Date.parse(document.created_at))) {
            throw Error('This is not a supported freETarget sync file.');
        }
        const data = object(document.data, 'Sync data');
        if (!hasExactKeys(data, ['profiles', 'history', 'settings'])) {
            throw Error('The sync file data is incomplete.');
        }
        validateRecordArrays(data.profiles, data.history);
        validateSettings(data.settings);
        return document;
    }

    function makeDocument(storage, source) {
        if (!['android', 'windows'].includes(source)) throw Error('Unknown sync source.');
        const profiles = parseLocal(storage, PROFILE_KEY, 'profile');
        const history = parseLocal(storage, HISTORY_KEY, 'session');
        validateRecordArrays(profiles, history);
        const settings = Object.create(null);
        for (const key of SETTINGS) settings[key] = storage.getItem(key);
        return validateDocument({
            format: FORMAT,
            schema: SCHEMA,
            created_at: new Date().toISOString(),
            source,
            data: { profiles, history, settings }
        });
    }

    function inspect(document, storage) {
        validateDocument(document);
        const profiles = parseLocal(storage, PROFILE_KEY, 'profile');
        const history = parseLocal(storage, HISTORY_KEY, 'session');
        validateRecordArrays(profiles, history);
        const profileIds = new Map(profiles.map(profile => [rowId(profile), profile]));
        const profileNames = new Map(profiles.map(profile => [profile.name.trim().toLowerCase(), profile]));
        const profileConflicts = [];
        let profilesAdded = 0;
        for (const profile of document.data.profiles) {
            const id = rowId(profile);
            if (profileIds.has(id)) {
                if (canonical(profileIds.get(id)) !== canonical(profile)) {
                    profileConflicts.push({ id, name: profile.name });
                }
            } else {
                const named = profileNames.get(profile.name.trim().toLowerCase());
                if (named && rowId(named) !== id) {
                    throw Error('A profile named "' + profile.name +
                        '" has a different ID on each device. Rename it on one device, then sync again.');
                }
                profilesAdded++;
                profileIds.set(id, profile);
                profileNames.set(profile.name.trim().toLowerCase(), profile);
            }
        }
        const historyIds = new Map(history.map(session => [rowId(session), session]));
        let sessionsAdded = 0, sessionVersions = 0;
        for (const session of document.data.history) {
            const id = rowId(session);
            if (!historyIds.has(id)) {
                sessionsAdded++;
                historyIds.set(id, null);
            } else if (historyIds.get(id) &&
                    canonical(historyIds.get(id)) !== canonical(session)) {
                sessionVersions++;
            }
        }
        const settingConflicts = [];
        for (const key of SETTINGS) {
            if (!hasOwn(document.data.settings, key)) continue;
            if (storage.getItem(key) !== document.data.settings[key]) settingConflicts.push(key);
        }
        return { profilesAdded, sessionsAdded, sessionVersions, profileConflicts, settingConflicts };
    }

    function merge(document, storage, options) {
        const summary = inspect(document, storage);
        const resolveProfile = options && options.resolveProfile;
        const profiles = parseLocal(storage, PROFILE_KEY, 'profile').slice();
        const profileIds = new Map(profiles.map((profile, index) => [rowId(profile), index]));
        for (const profile of document.data.profiles) {
            const id = rowId(profile);
            const index = profileIds.get(id);
            if (index === undefined) {
                profiles.push(profile);
                profileIds.set(id, profiles.length - 1);
            } else if (canonical(profiles[index]) !== canonical(profile) &&
                    typeof resolveProfile === 'function' && resolveProfile(profiles[index], profile)) {
                profiles[index] = profile;
            }
        }
        validateRecordArrays(profiles, []);

        const history = parseLocal(storage, HISTORY_KEY, 'session').slice();
        const historyById = new Map(history.map((session, index) => [rowId(session), index]));
        for (const session of document.data.history) {
            const id = rowId(session);
            const index = historyById.get(id);
            if (index === undefined) {
                history.push(session);
                historyById.set(id, history.length - 1);
            } else if (canonical(history[index]) !== canonical(session)) {
                const variantId = id + '-sync-' + hash(canonical(session));
                const variant = Object.assign({}, session, { id: variantId });
                const variantIndex = historyById.get(variantId);
                if (variantIndex === undefined) {
                    history.push(variant);
                    historyById.set(variantId, history.length - 1);
                } else if (canonical(history[variantIndex]) !== canonical(variant)) {
                    throw Error('A session conflict could not be merged safely.');
                }
            }
        }

        const updates = Object.create(null);
        if (canonical(profiles) !== canonical(parseLocal(storage, PROFILE_KEY, 'profile'))) {
            updates[PROFILE_KEY] = JSON.stringify(profiles);
        }
        if (canonical(history) !== canonical(parseLocal(storage, HISTORY_KEY, 'session'))) {
            updates[HISTORY_KEY] = JSON.stringify(history);
        }
        const acceptSettings = summary.settingConflicts.length === 0 ||
            (options && typeof options.resolveSettings === 'function' &&
                options.resolveSettings(summary.settingConflicts.map(key => ({
                    key, label: SETTING_LABELS[key]
                }))));
        for (const key of SETTINGS) {
            if (!hasOwn(document.data.settings, key)) continue;
            const incoming = document.data.settings[key];
            if (acceptSettings && storage.getItem(key) !== incoming) updates[key] = incoming;
        }
        return {
            updates,
            summary: Object.assign({}, summary, {
                profilesAdded: summary.profilesAdded,
                sessionsAdded: summary.sessionsAdded,
                sessionVersions: Math.max(0, history.length -
                    parseLocal(storage, HISTORY_KEY, 'session').length - summary.sessionsAdded)
            })
        };
    }

    return Object.freeze({ SETTINGS, SETTING_LABELS, FORMAT, SCHEMA, makeDocument, validateDocument, inspect, merge });
});
