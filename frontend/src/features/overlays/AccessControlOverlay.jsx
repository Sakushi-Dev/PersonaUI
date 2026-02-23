// ── AccessControlOverlay ──
// Pending requests, whitelist, blacklist management with 3s polling

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { ShieldIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { usePolling } from '../../hooks/usePolling';
import {
  getPendingRequests,
  getAccessLists,
  approveRequest,
  denyRequest,
  removeFromWhitelist,
  removeFromBlacklist,
} from '../../services/accessApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function AccessControlOverlay({ open, onClose, panelOnly }) {
  const { t } = useLanguage();
  const s = t('accessControl');

  const [pending, setPending] = useState([]);
  const [whitelist, setWhitelist] = useState([]);
  const [blacklist, setBlacklist] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [pendingData, listsData] = await Promise.all([
        getPendingRequests(),
        getAccessLists(),
      ]);
      // pending is an object { ip: { timestamp, status, waiting_seconds } }
      const pendingObj = pendingData.pending || {};
      setPending(Object.keys(pendingObj));
      setWhitelist(listsData.whitelist || []);
      setBlacklist(listsData.blacklist || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (open) {
      setLoading(true);
      refresh();
    }
  }, [open, refresh]);

  // Poll every 3 seconds while overlay is open
  usePolling(refresh, 3000, open);

  const handleApprove = async (ip) => {
    await approveRequest(ip);
    refresh();
  };

  const handleDeny = async (ip) => {
    await denyRequest(ip);
    refresh();
  };

  const handleRemoveWhitelist = async (ip) => {
    await removeFromWhitelist(ip);
    refresh();
  };

  const handleRemoveBlacklist = async (ip) => {
    await removeFromBlacklist(ip);
    refresh();
  };

  return (
    <Overlay open={open} onClose={onClose} width="500px" panelOnly={panelOnly}>
      <OverlayHeader title={s.title} icon={<ShieldIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        {loading ? (
          <div className={styles.centeredContent}>
            <Spinner />
          </div>
        ) : (
          <>
            {/* ═══ Section: Ausstehende Anfragen ═══ */}
            <div className={styles.ifaceSection}>
              <h3 className={styles.ifaceSectionTitle}>
                {s.pendingRequests}
                {pending.length > 0 && (
                  <span className={styles.accessBadgePending}>{pending.length}</span>
                )}
              </h3>
              <div className={styles.ifaceCard}>
                {pending.length === 0 ? (
                  <div className={styles.accessEmptyState}>
                    <span className={styles.ifaceToggleHint}>{s.noPending}</span>
                  </div>
                ) : (
                  <ul className={styles.accessList}>
                    {pending.map((ip, idx) => (
                      <li key={ip}>
                        <div className={styles.accessRow}>
                          <code className={styles.accessIp}>{ip}</code>
                          <div className={styles.accessActions}>
                            <button
                              className={styles.accessBtnApprove}
                              onClick={() => handleApprove(ip)}
                              title={s.approve}
                              type="button"
                            >
                              {s.approve}
                            </button>
                            <button
                              className={styles.accessBtnDeny}
                              onClick={() => handleDeny(ip)}
                              title={s.deny}
                              type="button"
                            >
                              {s.deny}
                            </button>
                          </div>
                        </div>
                        {idx < pending.length - 1 && <div className={styles.ifaceDivider} />}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* ═══ Section: Whitelist ═══ */}
            <div className={styles.ifaceSection}>
              <h3 className={styles.ifaceSectionTitle}>
                {s.whitelist}
                <span className={styles.accessBadgeCount}>{whitelist.length}</span>
              </h3>
              <div className={styles.ifaceCard}>
                {whitelist.length === 0 ? (
                  <div className={styles.accessEmptyState}>
                    <span className={styles.ifaceToggleHint}>{s.noEntries}</span>
                  </div>
                ) : (
                  <ul className={styles.accessList}>
                    {whitelist.map((ip, idx) => (
                      <li key={ip}>
                        <div className={styles.accessRow}>
                          <code className={styles.accessIp}>{ip}</code>
                          <button
                            className={styles.accessBtnRemove}
                            onClick={() => handleRemoveWhitelist(ip)}
                            title={s.remove}
                            type="button"
                          >
                            {s.remove}
                          </button>
                        </div>
                        {idx < whitelist.length - 1 && <div className={styles.ifaceDivider} />}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* ═══ Section: Blacklist ═══ */}
            <div className={styles.ifaceSection}>
              <h3 className={styles.ifaceSectionTitle}>
                {s.blacklist}
                <span className={styles.accessBadgeCount}>{blacklist.length}</span>
              </h3>
              <div className={styles.ifaceCard}>
                {blacklist.length === 0 ? (
                  <div className={styles.accessEmptyState}>
                    <span className={styles.ifaceToggleHint}>{s.noEntries}</span>
                  </div>
                ) : (
                  <ul className={styles.accessList}>
                    {blacklist.map((ip, idx) => (
                      <li key={ip}>
                        <div className={styles.accessRow}>
                          <code className={styles.accessIp}>{ip}</code>
                          <button
                            className={styles.accessBtnRemove}
                            onClick={() => handleRemoveBlacklist(ip)}
                            title={s.remove}
                            type="button"
                          >
                            {s.remove}
                          </button>
                        </div>
                        {idx < blacklist.length - 1 && <div className={styles.ifaceDivider} />}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </>
        )}
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>{s.close}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
