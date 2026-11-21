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
    });

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
