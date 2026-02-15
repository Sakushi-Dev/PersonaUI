// ── ServerSettingsOverlay ──
// Server mode + access control toggle

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import Toggle from '../../components/Toggle/Toggle';
import Button from '../../components/Button/Button';
import { getServerSettings, saveAndRestartServer } from '../../services/serverApi';
import { toggleAccessControl } from '../../services/accessApi';
import styles from './Overlays.module.css';

export default function ServerSettingsOverlay({ open, onClose }) {
  const [serverMode, setServerMode] = useState('local');
  const [port, setPort] = useState('5000');
  const [accessControlEnabled, setAccessControlEnabled] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      getServerSettings().then((data) => {
        setServerMode(data.server_mode || 'local');
        setPort(String(data.port || '5000'));
        setAccessControlEnabled(data.access_control_enabled !== false);
      }).catch(() => {});
    }
  }, [open]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await toggleAccessControl(accessControlEnabled);
      await saveAndRestartServer(serverMode, port);
      // Server will restart — page will become unresponsive shortly
    } catch (err) {
      console.error('Server restart failed:', err);
    } finally {
      setSaving(false);
    }
  }, [serverMode, port, accessControlEnabled]);

  return (
    <Overlay open={open} onClose={onClose} width="460px">
      <OverlayHeader title="Server-Einstellungen" onClose={onClose} />
      <OverlayBody>
        <FormGroup label="Server-Modus">
          <select
            className={styles.select}
            value={serverMode}
            onChange={(e) => setServerMode(e.target.value)}
          >
            <option value="local">Lokal (127.0.0.1)</option>
            <option value="public">Öffentlich (0.0.0.0 - Listen)</option>
          </select>
        </FormGroup>

        <FormGroup label="Port">
          <input
            className={styles.textInput}
            type="number"
            value={port}
            onChange={(e) => setPort(e.target.value)}
            min="1024"
            max="65535"
            placeholder="5000"
          />
        </FormGroup>

        <div className={styles.settingRow}>
          <Toggle
            label={accessControlEnabled ? 'Aktiv' : 'Inaktiv'}
            checked={accessControlEnabled}
            onChange={setAccessControlEnabled}
            id="access-control"
          />
          <div className={styles.settingInfo}>
            <p className={styles.settingLabel}>Zugangskontrolle</p>
            <p className={styles.hint}>
              IP-basierte Zugriffskontrolle für den öffentlichen Modus.
            </p>
          </div>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Abbrechen</Button>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Startet neu...' : 'Speichern & Neustarten'}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
