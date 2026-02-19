// ── AccessNotification ──
// Floating notification bar for pending access requests (host only).
// Polls /api/access/pending only while `polling` prop is true.

import { useState, useEffect, useCallback, useRef } from 'react';
import { getServerSettings } from '../../../../services/serverApi';
import { getPendingRequests, approveRequest, denyRequest } from '../../../../services/accessApi';
import styles from './AccessNotification.module.css';

export default function AccessNotification({ polling = false }) {
  const [notificationIp, setNotificationIp] = useState(null);
  const [visible, setVisible] = useState(false);
  const knownRef = useRef(new Set());
  const pollRef = useRef(null);
  const activeRef = useRef(false);

  // Check server mode once on mount
  useEffect(() => {
    let cancelled = false;
    getServerSettings()
      .then((data) => {
        if (!cancelled && data.server_mode === 'listen') {
          activeRef.current = true;
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Start / stop polling based on `polling` prop
  useEffect(() => {
    if (polling && activeRef.current) {
      startPolling();
    } else {
      stopPolling();
    }
    return () => stopPolling();
  }, [polling]); // eslint-disable-line react-hooks/exhaustive-deps

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    checkPending(); // immediate
    pollRef.current = setInterval(checkPending, 3000);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const checkPending = useCallback(async () => {
    try {
      const data = await getPendingRequests();
      if (!data.pending) return;

      const pendingObj = data.pending;
      const ips = Object.keys(pendingObj);

      // Detect new IPs
      for (const ip of ips) {
        if (!knownRef.current.has(ip)) {
          knownRef.current.add(ip);
          setNotificationIp(ip);
          setVisible(true);
        }
      }

      // Cleanup removed
      for (const ip of knownRef.current) {
        if (!ips.includes(ip)) {
          knownRef.current.delete(ip);
        }
      }

      // Hide if none left
      if (ips.length === 0) {
        setVisible(false);
        setNotificationIp(null);
      }
    } catch {
      // silent
    }
  }, []);

  const handleApprove = useCallback(async () => {
    if (!notificationIp) return;
    try {
      await approveRequest(notificationIp);
      knownRef.current.delete(notificationIp);
      setVisible(false);
      setNotificationIp(null);
      // Will pick up next pending IP on next poll
    } catch {
      // silent
    }
  }, [notificationIp]);

  const handleDeny = useCallback(async () => {
    if (!notificationIp) return;
    try {
      await denyRequest(notificationIp);
      knownRef.current.delete(notificationIp);
      setVisible(false);
      setNotificationIp(null);
    } catch {
      // silent
    }
  }, [notificationIp]);

  if (!visible || !notificationIp) return null;

  return (
    <div className={styles.notification}>
      <div className={styles.content}>
        <span className={styles.icon}>🔔</span>
        <span className={styles.text}>
          <strong>{notificationIp}</strong> fragt Zugang an
        </span>
        <div className={styles.actions}>
          <button className={styles.approveBtn} onClick={handleApprove} title="Genehmigen">✓</button>
          <button className={styles.denyBtn} onClick={handleDeny} title="Ablehnen">✕</button>
        </div>
      </div>
    </div>
  );
}
