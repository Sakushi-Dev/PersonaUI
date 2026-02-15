// ── DebugOverlay ──
// Debug panel with toast tests, memory buttons, session info

import { useState, useCallback } from 'react';
import { useSession } from '../../hooks/useSession';
import { useToast } from '../../components/Toast/ToastContainer';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { checkMemoryAvailability } from '../../services/memoryApi';
import styles from './Overlays.module.css';

export default function DebugOverlay({ open, onClose }) {
  const { sessionId, personaId, chatHistory, totalMessageCount } = useSession();
  const toast = useToast();

  const [sessionInfo, setSessionInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);

  const refreshInfo = useCallback(async () => {
    if (!sessionId) return;
    setLoadingInfo(true);
    try {
      const data = await checkMemoryAvailability(sessionId);
      setSessionInfo(data);
    } catch {
      setSessionInfo({ error: 'Failed to load' });
    } finally {
      setLoadingInfo(false);
    }
  }, [sessionId]);

  return (
    <Overlay open={open} onClose={onClose} width="520px">
      <OverlayHeader title="🛠 Debug Panel" onClose={onClose} />
      <OverlayBody>
        {/* Toast Notifications */}
        <section className={styles.section}>
          <h4 className={styles.sectionTitle}>Toast Notifications</h4>
          <div className={styles.buttonGrid}>
            <Button size="sm" variant="secondary" onClick={() => toast.info('Info-Nachricht')}>
              Info
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.success('Erfolg!')}>
              Success
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.warning('Warnung!')}>
              Warning
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.error('Fehler aufgetreten!')}>
              Error
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.info('Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')}>
              Truncation
            </Button>
          </div>
        </section>

        {/* Page Tools */}
        <section className={styles.section}>
          <h4 className={styles.sectionTitle}>Page Tools</h4>
          <div className={styles.buttonGrid}>
            <Button size="sm" variant="secondary" onClick={() => window.location.reload()}>
              🔄 Page Reload
            </Button>
          </div>
        </section>

        {/* Session Info */}
        <section className={styles.section}>
          <h4 className={styles.sectionTitle}>
            Session Info
            <button className={styles.iconBtn} onClick={refreshInfo} title="Aktualisieren">🔄</button>
          </h4>

          {loadingInfo ? (
            <Spinner />
          ) : (
            <div className={styles.debugGrid}>
              <div className={styles.debugRow}>
                <span>Session ID:</span>
                <code>{sessionId || '-'}</code>
              </div>
              <div className={styles.debugRow}>
                <span>Persona ID:</span>
                <code>{personaId || '-'}</code>
              </div>
              <div className={styles.debugRow}>
                <span>Messages (total):</span>
                <code>{totalMessageCount}</code>
              </div>
              <div className={styles.debugRow}>
                <span>Messages (loaded):</span>
                <code>{chatHistory.length}</code>
              </div>
              {sessionInfo && !sessionInfo.error && (
                <>
                  <div className={styles.debugRow}>
                    <span>Last Memory Marker:</span>
                    <code>{sessionInfo.last_marker || '-'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>User msgs since marker:</span>
                    <code>{sessionInfo.user_messages_since_marker ?? '-'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>Memory Available:</span>
                    <code>{sessionInfo.available ? '✅' : '❌'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>Context Ratio:</span>
                    <code>{sessionInfo.context_ratio ?? '-'}</code>
                  </div>
                </>
              )}
            </div>
          )}
        </section>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
      </OverlayFooter>
    </Overlay>
  );
}
