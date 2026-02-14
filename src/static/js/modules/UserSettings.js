/**
 * UserSettings - Zentrale Settings-Verwaltung (serverseitig gespeichert)
 * 
 * Ersetzt localStorage für alle App-Settings.
 * Settings werden beim Start vom Server geladen und bei Änderungen zurückgeschrieben.
 * 
 * Nutzung:
 *   import { UserSettings } from './modules/UserSettings.js';
 *   await UserSettings.load();              // einmal beim App-Start
 *   UserSettings.get('darkMode');            // lesen
 *   UserSettings.set('darkMode', true);      // schreiben (speichert sofort auf Server)
 *   UserSettings.setMany({a: 1, b: 2});      // mehrere auf einmal
 */

class _UserSettings {
    constructor() {
        this._settings = {};
        this._defaults = {};
        this._loaded = false;
        this._saveTimeout = null;
        this._pendingChanges = {};
    }

    /**
     * Lädt Settings vom Server. Muss vor get/set aufgerufen werden.
     */
    async load() {
        try {
            const res = await fetch('/api/user-settings');
            const data = await res.json();
            if (data.success) {
                this._settings = data.settings;
                if (data.defaults) {
                    this._defaults = data.defaults;
                }
            } else {
                console.error('UserSettings: Laden fehlgeschlagen', data.error);
            }
        } catch (e) {
            console.error('UserSettings: Server nicht erreichbar', e);
        }
        this._loaded = true;
    }

    /**
     * Gibt einen Setting-Wert zurück.
     * @param {string} key - Setting-Name
     * @param {*} fallback - Fallback falls nicht vorhanden
     */
    get(key, fallback = null) {
        if (!this._loaded) {
            console.warn('UserSettings: get() aufgerufen bevor load() fertig');
        }
        const val = this._settings[key];
        return val !== undefined && val !== null ? val : fallback;
    }

    /**
     * Gibt einen Default-Wert zurück (vom Server geliefert).
     * @param {string} key - Setting-Name
     * @param {*} fallback - Fallback falls nicht vorhanden
     */
    getDefault(key, fallback = null) {
        const val = this._defaults[key];
        return val !== undefined && val !== null ? val : fallback;
    }

    /**
     * Setzt einen Setting-Wert und speichert debounced auf den Server.
     */
    set(key, value) {
        this._settings[key] = value;
        this._pendingChanges[key] = value;
        this._debounceSave();
    }

    /**
     * Setzt mehrere Settings auf einmal.
     */
    setMany(obj) {
        for (const [key, value] of Object.entries(obj)) {
            this._settings[key] = value;
            this._pendingChanges[key] = value;
        }
        this._debounceSave();
    }

    /**
     * Gibt alle Settings als Objekt zurück.
     */
    getAll() {
        return { ...this._settings };
    }

    /**
     * Debounced save – wartet 300ms und sendet dann alle ausstehenden Änderungen.
     */
    _debounceSave() {
        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
        }
        this._saveTimeout = setTimeout(() => {
            this._flush();
        }, 300);
    }

    /**
     * Sendet ausstehende Änderungen sofort an den Server.
     */
    async _flush() {
        const changes = { ...this._pendingChanges };
        this._pendingChanges = {};

        if (Object.keys(changes).length === 0) return;

        try {
            const res = await fetch('/api/user-settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(changes)
            });
            const data = await res.json();
            if (!data.success) {
                console.error('UserSettings: Speichern fehlgeschlagen', data.error);
            }
        } catch (e) {
            console.error('UserSettings: Speichern fehlgeschlagen', e);
        }
    }

    /**
     * Erzwingt sofortiges Speichern (z.B. vor Navigation).
     */
    async save() {
        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
            this._saveTimeout = null;
        }
        await this._flush();
    }

    /**
     * Setzt alle Settings auf Server-Defaults zurück.
     */
    async reset() {
        try {
            const res = await fetch('/api/user-settings/reset', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                this._settings = data.settings;
                this._pendingChanges = {};
                if (data.defaults) {
                    this._defaults = data.defaults;
                }
            }
            return data.success;
        } catch (e) {
            console.error('UserSettings: Reset fehlgeschlagen', e);
            return false;
        }
    }
}

// Singleton-Instanz
export const UserSettings = new _UserSettings();
