// ── AccessControlOverlay ──
// Pending requests, whitelist, blacklist management with 3s polling

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
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
import styles from './Overlays.module.css';

export default function AccessControlOverlay({ open, onClose }) {
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
    <Overlay open={open} onClose={onClose} width="500px">
      <OverlayHeader title="🛡️ Zugangskontrolle" onClose={onClose} />
      <OverlayBody>
        {loading ? (
          <Spinner />
        ) : (
          <>
            {/* Pending Requests */}
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                Ausstehende Anfragen
                {pending.length > 0 && <span className={styles.badge}>{pending.length}</span>}
              </h3>
              {pending.length === 0 ? (
                <p className={styles.emptyText}>Keine ausstehenden Anfragen</p>
              ) : (
                <ul className={styles.ipListVertical}>
                  {pending.map((ip) => (
                    <li key={ip} className={styles.ipItem}>
                      <code>{ip}</code>
                      <div className={styles.ipActions}>
                        <button className={styles.approveBtn} onClick={() => handleApprove(ip)} title="Genehmigen">✓</button>
                        <button className={styles.denyBtn} onClick={() => handleDeny(ip)} title="Ablehnen">✕</button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Whitelist */}
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                Whitelist
                <span className={styles.badge}>{whitelist.length}</span>
              </h3>
              {whitelist.length === 0 ? (
                <p className={styles.emptyText}>Keine Einträge</p>
              ) : (
                <ul className={styles.ipListVertical}>
                  {whitelist.map((ip) => (
                    <li key={ip} className={styles.ipItem}>
                      <code>{ip}</code>
                      <button className={styles.removeBtn} onClick={() => handleRemoveWhitelist(ip)} title="Entfernen">✕</button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Blacklist */}
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                Blacklist
                <span className={styles.badge}>{blacklist.length}</span>
              </h3>
              {blacklist.length === 0 ? (
                <p className={styles.emptyText}>Keine Einträge</p>
              ) : (
                <ul className={styles.ipListVertical}>
                  {blacklist.map((ip) => (
                    <li key={ip} className={styles.ipItem}>
                      <code>{ip}</code>
                      <button className={styles.removeBtn} onClick={() => handleRemoveBlacklist(ip)} title="Entfernen">✕</button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
      </OverlayFooter>
    </Overlay>
  );
}
