// ── DebugOverlay ──
// Debug panel with toast tests, cortex status, session info

import { useState, useCallback } from 'react';
import { useSession } from '../../hooks/useSession';
import { useToast } from '../../components/Toast/ToastContainer';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { WrenchIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getCortexFiles } from '../../services/cortexApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function DebugOverlay({ open, onClose }) {
  const { sessionId, personaId, chatHistory, totalMessageCount } = useSession();
  const toast = useToast();
  const { t } = useLanguage();
  const s = t('debug');

  const [sessionInfo, setSessionInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);

  const refreshInfo = useCallback(async () => {
    if (!personaId) return;
    setLoadingInfo(true);
    try {
      const data = await getCortexFiles(personaId);
      setSessionInfo({ session_id: sessionId, ...data });
    } catch {
      setSessionInfo({ error: 'Failed to load' });
    } finally {
      setLoadingInfo(false);
    }
  }, [personaId, sessionId]);

  return (
    <Overlay open={open} onClose={onClose} width="520px">
      <OverlayHeader title={s.title} icon={<WrenchIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        {/* Toast Notifications */}
        <section className={styles.section}>
          <h4 className={styles.sectionTitle}>{s.toastSection}</h4>
          <div className={styles.buttonGrid}>
            <Button size="sm" variant="secondary" onClick={() => toast.info(s.infoToast)}>
              Info
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.success(s.successToast)}>
              Success
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.warning(s.warningToast)}>
              Warning
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.error(s.errorToast)}>
              Error
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast.info('Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')}>
              Truncation
            </Button>
          </div>
        </section>

        {/* Page Tools */}
        <section className={styles.section}>
          <h4 className={styles.sectionTitle}>{s.pageTools}</h4>
          <div className={styles.buttonGrid}>
            <Button size="sm" variant="secondary" onClick={() => window.location.reload()}>
              🔄 Page Reload
            </Button>
          </div>
        </section>

        {/* Session Info */}
        <section className={styles.section}>
          <h4 className={styles.sectionTitle}>
            {s.sessionInfo}
            <button className={styles.iconBtn} onClick={refreshInfo} title={s.refresh}>🔄</button>
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

              {sessionInfo && !sessionInfo.error && sessionInfo.files && (
                <>
                  <div className={styles.debugRow}>
                    <span>Cortex Files:</span>
                    <code>{Object.keys(sessionInfo.files).join(', ')}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>memory.md:</span>
                    <code>{sessionInfo.files.memory ? `${sessionInfo.files.memory.length} chars` : '-'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>soul.md:</span>
                    <code>{sessionInfo.files.soul ? `${sessionInfo.files.soul.length} chars` : '-'}</code>
                  </div>
                  <div className={styles.debugRow}>
                    <span>relationship.md:</span>
                    <code>{sessionInfo.files.relationship ? `${sessionInfo.files.relationship.length} chars` : '-'}</code>
                  </div>
                </>
              )}

            </div>
          )}
        </section>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>{s.close}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
