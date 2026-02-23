// ── DisclaimerOverlay ──
// Shown after onboarding — warns users about the fictional nature of AI personas

import { useState } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import { ShieldIcon } from '../../components/Icons/Icons';
import { apiPost } from '../../services/apiClient';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './DisclaimerOverlay.module.css';

export default function DisclaimerOverlay({ open, onAccept }) {
  const [loading, setLoading] = useState(false);
  const { t } = useLanguage();
  const s = t('disclaimer');

  const handleAccept = async () => {
    setLoading(true);
    try {
      await apiPost('/api/onboarding/accept-disclaimer');
      onAccept?.();
    } catch {
      // Still allow proceeding on error
      onAccept?.();
    } finally {
      setLoading(false);
    }
  };

  const handleQuit = async () => {
    try {
      await apiPost('/api/shutdown');
    } catch {
      // Server might be shutting down already
    }
    // Close the browser tab/window
    window.close();
    // Fallback: show message if window.close() is blocked
    setTimeout(() => {
      document.body.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#888;"><p>${s.fallbackText}</p></div>`;
    }, 500);
  };

  return (
    <Overlay open={open} onClose={() => {}} width="520px">
      <OverlayHeader title={s.title} icon={<ShieldIcon size={20} />} />

      <OverlayBody>
        <div className={styles.disclaimerContent}>
          <div className={styles.warningBanner}>
            <span className={styles.warningEmoji}>⚠️</span>
            <span>{s.warningBanner}</span>
          </div>

          <h3 className={styles.sectionTitle}>{s.fictionTitle}</h3>
          <p
            className={styles.text}
            dangerouslySetInnerHTML={{ __html: s.fictionText }}
          />

          <h3 className={styles.sectionTitle}>{s.aiErrorTitle}</h3>
          <p className={styles.text}>{s.aiErrorText}</p>

          <div className={styles.articleLink}>
            <span className={styles.linkIcon}>📖</span>
            <span>
              {s.articleIntro}{' '}
              <a
                href="https://en.wikipedia.org/wiki/Chatbot_psychosis"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.link}
              >
                {s.articleLinkText}
              </a>.
            </span>
          </div>
        </div>
      </OverlayBody>

      <OverlayFooter>
        <Button variant="danger" onClick={handleQuit}>
          {s.quitBtn}
        </Button>
        <Button variant="primary" onClick={handleAccept} disabled={loading}>
          {loading ? s.savingText : s.acceptBtn}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
