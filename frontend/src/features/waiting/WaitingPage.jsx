import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { requestAccess, pollAccessStatus } from '../../services/accessApi';
import Spinner from '../../components/Spinner/Spinner';
import styles from './WaitingPage.module.css';

const STATUS_MESSAGES = {
  pending: {
    icon: '⏳',
    title: 'Zugang angefragt',
    text: 'Deine Anfrage wurde gesendet. Warte auf Freigabe...',
    color: 'pending',
  },
  approved: {
    icon: '✅',
    title: 'Zugang gewährt!',
    text: 'Du wirst weitergeleitet...',
    color: 'success',
  },
  denied: {
    icon: '🚫',
    title: 'Zugang verweigert',
    text: 'Deine Anfrage wurde abgelehnt.',
    color: 'error',
  },
  expired: {
    icon: '⏰',
    title: 'Anfrage abgelaufen',
    text: 'Deine Anfrage ist abgelaufen. Bitte versuche es erneut.',
    color: 'warning',
  },
  rate_limited: {
    icon: '⚠️',
    title: 'Zu viele Anfragen',
    text: 'Bitte warte einige Minuten und versuche es dann erneut.',
    color: 'warning',
  },
  error: {
    icon: '❌',
    title: 'Fehler',
    text: 'Es ist ein Fehler aufgetreten. Bitte versuche es erneut.',
    color: 'error',
  },
};

export default function WaitingPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState(null);
  const pollRef = useRef(null);
  const hasRequested = useRef(false);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);

    pollRef.current = setInterval(async () => {
      try {
        const res = await pollAccessStatus();
        if (res.status === 'approved') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setStatus('approved');
          setMessage(STATUS_MESSAGES.approved);
          setTimeout(() => navigate('/'), 1500);
        } else if (res.status === 'denied') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setStatus('denied');
          setMessage(STATUS_MESSAGES.denied);
        } else if (res.status === 'expired') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setStatus('expired');
          setMessage(STATUS_MESSAGES.expired);
        }
        // pending → keep polling
      } catch {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setStatus('error');
        setMessage(STATUS_MESSAGES.error);
      }
    }, 2000);
  }, [navigate]);

  const sendRequest = useCallback(async () => {
    setStatus('loading');
    setMessage(null);
    try {
      const res = await requestAccess();
      if (res.status === 'approved' || res.already_approved) {
        setStatus('approved');
        setMessage(STATUS_MESSAGES.approved);
        setTimeout(() => navigate('/'), 1500);
        return;
      }
      if (res.status === 'rate_limited') {
        setStatus('rate_limited');
        setMessage(STATUS_MESSAGES.rate_limited);
        return;
      }
      // pending
      setStatus('pending');
      setMessage(STATUS_MESSAGES.pending);
      startPolling();
    } catch {
      setStatus('error');
      setMessage(STATUS_MESSAGES.error);
    }
  }, [navigate, startPolling]);

  useEffect(() => {
    if (!hasRequested.current) {
      hasRequested.current = true;
      sendRequest();
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sendRequest]);

  const canRetry = status === 'expired' || status === 'error' || status === 'denied';

  return (
    <div className={styles.page}>
      {/* Animated background orbs */}
      <div className={styles.orb} style={{ top: '20%', left: '15%', animationDelay: '0s' }} />
      <div className={styles.orb} style={{ top: '60%', right: '10%', animationDelay: '2s' }} />
      <div className={styles.orb} style={{ bottom: '15%', left: '40%', animationDelay: '4s' }} />

      <div className={styles.card}>
        {status === 'loading' ? (
          <div className={styles.loadingSection}>
            <Spinner size={48} />
            <p className={styles.loadingText}>Verbindung wird hergestellt...</p>
          </div>
        ) : message ? (
          <>
            <div className={`${styles.iconWrap} ${styles[message.color]}`}>
              <span className={styles.statusIcon}>{message.icon}</span>
              {status === 'pending' && <div className={styles.pulse} />}
            </div>
            <h1 className={styles.title}>{message.title}</h1>
            <p className={styles.text}>{message.text}</p>

            {status === 'pending' && (
              <div className={styles.dots}>
                <span className={styles.dot} style={{ animationDelay: '0s' }} />
                <span className={styles.dot} style={{ animationDelay: '0.2s' }} />
                <span className={styles.dot} style={{ animationDelay: '0.4s' }} />
              </div>
            )}

            {canRetry && (
              <button className={styles.retryBtn} onClick={sendRequest}>
                Erneut versuchen
              </button>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
