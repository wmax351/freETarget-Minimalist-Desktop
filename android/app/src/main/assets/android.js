(() => {
    'use strict';

    const target = window.FTAndroidTarget;
    if (target.isTablet()) document.documentElement.dataset.formFactor = 'tablet';

    const storage = window.localStorage;
    window.FTDesktopStorage = {
        getItem(key) {
            return storage.getItem(key);
        },
        setItem: (key, value) => storage.setItem(key, value),
        removeItem: key => storage.removeItem(key),
        key: index => storage.key(index),
        get length() { return storage.length; }
    };

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelector('.footerVersion').textContent = 'freETarget Minimalist ' + target.versionName();
        const syncNavigationColor = () => {
            const dark = document.body.classList.contains('dark');
            const side = getComputedStyle(document.body).getPropertyValue('--side').trim();
            target.setNavigationAppearance(dark, side);
        };
        new MutationObserver(syncNavigationColor).observe(document.body, {
            attributes: true, attributeFilter: ['class', 'style']
        });
        syncNavigationColor();
        document.getElementById('settingsHost').autocapitalize = 'none';
        installPortableSync();
    });

    function installPortableSync() {
        const backup = document.getElementById('settingsBackup');
        const core = window.FTPortableSyncCore;
        if (!backup || !core) return;
        const desktopControls = backup.querySelector('.desktopDataControls');
        if (desktopControls) desktopControls.hidden = true;

        const panel = document.createElement('section');
        panel.className = 'desktopDataControls';
        const heading = document.createElement('h3');
        heading.textContent = 'Sync With Windows PC';
        const help = document.createElement('p');
        help.className = 'settingsHelp';
        help.textContent = 'Transfer a JSON sync file manually. Export on one device, import and merge on the other, then export again to carry merged data back. Sessions are merged; conflicting profile and setting edits ask before applying. Records missing from a file are kept. Connection details stay on this device. The file is not encrypted.';
        const actions = document.createElement('div');
        actions.className = 'formActions';
        const exportButton = document.createElement('button');
        exportButton.type = 'button';
        exportButton.className = 'btn';
        exportButton.textContent = 'Export Sync File';
        const importButton = document.createElement('button');
        importButton.type = 'button';
        importButton.className = 'btn';
        importButton.textContent = 'Import & Merge Sync File';
        const status = document.createElement('p');
        status.className = 'settingsHelp';
        status.setAttribute('role', 'status');
        actions.append(exportButton, importButton);
        panel.append(heading, help, actions, status);
        backup.insertBefore(panel, desktopControls);

        function ensureIdle() {
            const state = window.FTDesktopSessionState();
            if (state.active || state.unsaved) {
                throw new Error('Finish and save or discard the current session before syncing.');
            }
            if (state.connected) throw new Error('Disconnect the target before syncing.');
        }

        function apply(updates) {
            const previous = Object.create(null);
            try {
                for (const [key, value] of Object.entries(updates)) {
                    previous[key] = window.FTDesktopStorage.getItem(key);
                    if (value === null) window.FTDesktopStorage.removeItem(key);
                    else window.FTDesktopStorage.setItem(key, value);
                }
            } catch (error) {
                let rollbackError = null;
                for (const key of Object.keys(previous).reverse()) {
                    try {
                        if (previous[key] === null) window.FTDesktopStorage.removeItem(key);
                        else window.FTDesktopStorage.setItem(key, previous[key]);
                    } catch (rollbackFailure) {
                        rollbackError = rollbackFailure;
                    }
                }
                if (rollbackError) {
                    throw new Error('Sync failed and local rollback was incomplete. Keep the sync file as a recovery copy. ' + rollbackError.message);
                }
                throw new Error('Sync was not applied; local data was restored. ' + error.message);
            }
        }

        function importDocument(text) {
            ensureIdle();
            const document = JSON.parse(text);
            const storageView = window.FTDesktopStorage;
            const preview = core.inspect(document, storageView);
            const message = 'Sync file from ' + document.source + ' contains ' + preview.profilesAdded +
                ' new profiles, ' + preview.sessionsAdded + ' new sessions' +
                (preview.sessionVersions ? ' and ' + preview.sessionVersions +
                    ' conflicting session version(s) that will be preserved' : '') +
                '. It has ' + preview.profileConflicts.length + ' profile and ' +
                preview.settingConflicts.length + ' setting conflict(s). Continue to review conflicts?';
            if (!confirm(message)) {
                status.textContent = 'Sync canceled. Local data was not changed.';
                return;
            }
            const merged = core.merge(document, storageView, {
                resolveProfile: (local, incoming) => confirm('Profile "' + local.name +
                    '" differs from the sync file. Replace this device’s profile with the imported version? Cancel keeps the current profile.'),
                resolveSettings: items => confirm('These portable settings differ: ' +
                    items.map(item => item.label).join(', ') +
                    '. Use the sync-file values? Cancel keeps the current settings.')
            });
            if (!Object.keys(merged.updates).length) {
                status.textContent = 'No new data was merged.';
                return;
            }
            apply(merged.updates);
            status.textContent = 'Data merged. Export a new sync file and import it on the Windows PC to carry the merged data back.';
            window.setTimeout(() => window.location.reload(), 500);
        }

        exportButton.onclick = () => {
            try {
                ensureIdle();
                const document = core.makeDocument(window.FTDesktopStorage, 'android');
                target.exportSyncFile(JSON.stringify(document));
                status.textContent = 'Choose where to save the sync file…';
            } catch (error) {
                status.textContent = error.message;
            }
        };
        importButton.onclick = () => {
            try {
                ensureIdle();
                target.importSyncFile();
                status.textContent = 'Choose a sync file…';
            } catch (error) {
                status.textContent = error.message;
            }
        };
        window.FTPortableSync = {
            exportResult(success, message) {
                status.textContent = message;
            },
            importResult(text, error) {
                if (error) {
                    status.textContent = error;
                    return;
                }
                try {
                    importDocument(text);
                } catch (failure) {
                    status.textContent = failure.message;
                }
            }
        };
    }

    window.fetch = async (path, options = {}) => {
        if (typeof path !== 'string' || !/^\/api\/(events(?:\?after=\d+)?|serial-ports|connect|disconnect|clear-diagnostics)$/.test(path)) {
            throw new Error('This service is unavailable in the Android beta.');
        }
        const reply = JSON.parse(target.request(
            options.method || 'GET', path, options.body || '{}'
        ));
        return {
            ok: reply.status >= 200 && reply.status < 300,
            status: reply.status,
            json: async () => reply.body,
            text: async () => JSON.stringify(reply.body)
        };
    };
})();
