// ── ServerSettingsOverlay ──
// Server mode + access control toggle

import { useState, useEffect, useCallback, useRef } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { ServerIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import Toggle from '../../components/Toggle/Toggle';
import Button from '../../components/Button/Button';
import { getServerSettings, saveAndRestartServer, checkApiStatus } from '../../services/serverApi';
import { getAccessLists, toggleAccessControl } from '../../services/accessApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function ServerSettingsOverlay({ open, onClose, panelOnly }) {
  const { t } = useLanguage();
  const s = t('serverSettings');
  const sc = t('common');

  const [serverMode, setServerMode] = useState('local');
  const [accessControlEnabled, setAccessControlEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [restartMessage, setRestartMessage] = useState('');
  const restartTimerRef = useRef(null);

  // Load server mode + access control status on open
  useEffect(() => {
    if (open) {
      getServerSettings()
        .then((data) => setServerMode(data.server_mode || 'local'))
        .catch(() => {});
      getAccessLists()
        .then((data) => setAccessControlEnabled(data.access_control_enabled !== false))
        .catch(() => {});
    }
    return () => { if (restartTimerRef.current) clearTimeout(restartTimerRef.current); };
  }, [open]);

  // Toggle access control immediately (like legacy)
  const handleAccessToggle = useCallback(async (enabled) => {
    const prev = accessControlEnabled;
    setAccessControlEnabled(enabled);
    try {
      await toggleAccessControl(enabled);
    } catch {
      setAccessControlEnabled(prev); // revert on failure
    }
  }, [accessControlEnabled]);

  // Wait for server to come back after restart, then reload
  const waitForServerAndReload = useCallback(() => {
    let attempts = 0;
    const maxAttempts = 30;

    const check = () => {
      checkApiStatus()
        .then(() => { window.location.href = '/'; })
        .catch(() => {
          attempts++;
          if (attempts < maxAttempts) {
            restartTimerRef.current = setTimeout(check, 1000);
          } else {
            setRestartMessage(s.restartSlow);
            setRestarting(false);
          }
        });
    };

    restartTimerRef.current = setTimeout(check, 2000);
  }, []);

  // Save server mode and restart
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await saveAndRestartServer(serverMode);
      setRestarting(true);
      setRestartMessage(s.restarting);
      waitForServerAndReload();
    } catch (err) {
      console.error('Server restart failed:', err);
      setSaving(false);
    }
  }, [serverMode, waitForServerAndReload]);

  // Restart overlay (fullscreen)
  if (restarting) {
    return (
      <Overlay open={true} onClose={() => {}} width="100vw">
        <div className={styles.restartOverlay}>
          <div className={styles.restartIcon}>🔄</div>
          <div className={styles.restartText}>{restartMessage}</div>
          <p className={styles.hint}>{s.autoReload}</p>
          {restartMessage === s.restartSlow && (
            <Button variant="primary" onClick={() => { window.location.href = '/'; }} style={{ marginTop: 16 }}>
              {s.reloadPage}
            </Button>
          )}
        </div>
      </Overlay>
    );
  }

  return (
    <Overlay open={open} onClose={onClose} width="460px" panelOnly={panelOnly}>
      <OverlayHeader title={s.title} icon={<ServerIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        <FormGroup label={s.serverMode}>
          <select
            className={styles.select}
            value={serverMode}
            onChange={(e) => setServerMode(e.target.value)}
          >
            <option value="local">{s.local}</option>
            <option value="listen">{s.public}</option>
          </select>
          <p className={styles.hint} style={{ marginTop: 6 }} dangerouslySetInnerHTML={{ __html: `${s.localHint}<br />${s.publicHint}` }} />
        </FormGroup>

        {/* Access Control */}
        <div className={styles.settingRow}>
          <div className={styles.settingInfo}>
            <p className={styles.settingLabel}>🛡️ {s.accessControl}</p>
            <p className={styles.hint}>
              {s.accessControlHint}
            </p>
          </div>
          <Toggle
            label={accessControlEnabled ? s.accessActive : s.accessInactive}
            checked={accessControlEnabled}
            onChange={handleAccessToggle}
            id="access-control"
          />
        </div>

        <div className={styles.tipBox}>
          <p className={styles.hint}>
            ℹ️ <strong>Tipp:</strong> <span dangerouslySetInnerHTML={{ __html: s.tipAccess }} />
          </p>
        </div>

        <div className={styles.tipBox}>
          <p className={styles.hint}>
            ℹ️ <strong>Tipp:</strong> {s.tipRestart}
          </p>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>{sc.cancel}</Button>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? sc.saving : s.saveRestart}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
