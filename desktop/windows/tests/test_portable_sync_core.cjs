const assert = require('assert');
const core = require('../app/assets/portable_sync_core.js');

function storage(values = {}) {
    const data = new Map(Object.entries(values));
    return {
        getItem: key => data.has(key) ? data.get(key) : null,
        setItem: (key, value) => data.set(key, value),
        removeItem: key => data.delete(key),
        data
    };
}

function records(store, key) {
    return JSON.parse(store.getItem(key) || '[]');
}

const profile = { id: 'profile-1', name: 'Alex', guns: [{ id: 'gun-1', model: 'A' }] };
const session = { id: 'session-1', name: 'Alex', total: 95 };
const source = storage({
    'ft-shooter-profiles-v1': JSON.stringify([profile]),
    'ft-session-history-v1': JSON.stringify([session]),
    'ft-theme-mode': 'dark',
    'ft-host': '192.168.10.9'
});
const document = core.makeDocument(source, 'windows');

assert.strictEqual(document.format, 'freetarget-portable-sync');
assert.strictEqual(document.data.settings['ft-host'], undefined);
assert.strictEqual(document.data.settings['ft-theme-mode'], 'dark');

const destination = storage({
    'ft-shooter-profiles-v1': '[]',
    'ft-session-history-v1': '[]',
    'ft-theme-mode': 'light',
    'ft-host': '192.168.1.25'
});
const preview = core.inspect(document, destination);
assert.deepStrictEqual([preview.profilesAdded, preview.sessionsAdded, preview.settingConflicts.length], [1, 1, 1]);
const merged = core.merge(document, destination, { resolveSettings: () => false });
const applied = storage(Object.fromEntries(destination.data));
for (const [key, value] of Object.entries(merged.updates)) {
    if (value === null) applied.removeItem(key);
    else applied.setItem(key, value);
}
assert.deepStrictEqual(records(applied, 'ft-shooter-profiles-v1'), [profile]);
assert.strictEqual(merged.updates['ft-theme-mode'], undefined);
assert.strictEqual(destination.getItem('ft-host'), '192.168.1.25');

destination.setItem('ft-shooter-profiles-v1', JSON.stringify([profile]));
destination.setItem('ft-session-history-v1', JSON.stringify([session]));
destination.setItem('ft-theme-mode', 'light');
const localSession = { ...session, total: 90 };
destination.setItem('ft-session-history-v1', JSON.stringify([localSession]));
const conflict = core.merge(document, destination, { resolveSettings: () => true });
assert.strictEqual(JSON.parse(conflict.updates['ft-session-history-v1']).length, 2);
assert.strictEqual(conflict.updates['ft-theme-mode'], 'dark');
assert.strictEqual(core.merge(document, storage({
    'ft-shooter-profiles-v1': JSON.stringify([profile]),
    'ft-session-history-v1': conflict.updates['ft-session-history-v1'],
    'ft-theme-mode': 'dark'
})).updates['ft-session-history-v1'], undefined);

const changedProfile = { ...profile, notes: 'updated elsewhere' };
const profileConflictDoc = core.makeDocument(storage({
    'ft-shooter-profiles-v1': JSON.stringify([changedProfile]),
    'ft-session-history-v1': '[]'
}), 'android');
assert.strictEqual(core.merge(profileConflictDoc, storage({
    'ft-shooter-profiles-v1': JSON.stringify([profile]),
    'ft-session-history-v1': '[]'
}), { resolveProfile: () => false }).updates['ft-shooter-profiles-v1'], undefined);
assert.deepStrictEqual(JSON.parse(core.merge(profileConflictDoc, storage({
    'ft-shooter-profiles-v1': JSON.stringify([profile]),
    'ft-session-history-v1': '[]'
}), { resolveProfile: () => true }).updates['ft-shooter-profiles-v1']), [changedProfile]);

assert.throws(() => core.validateDocument({
    ...document,
    data: { ...document.data, settings: { ...document.data.settings, 'ft-host': 'host' } }
}), /non-portable/);
assert.throws(() => core.validateDocument({ ...document, extra: true }), /supported/);
console.log('Portable sync core tests passed.');
