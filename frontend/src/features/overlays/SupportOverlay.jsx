// ── SupportOverlay ──
// Ko-fi support overlay with project info

import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import { HeartIcon } from '../../components/Icons/Icons';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './SupportOverlay.module.css';

export default function SupportOverlay({ open, onClose, panelOnly }) {
  const { t } = useLanguage();
  const s = t('support');

  return (
    <Overlay open={open} onClose={onClose} width="480px" panelOnly={panelOnly}>
      <OverlayHeader
        title={s.title}
        icon={<HeartIcon size={20} />}
        onClose={onClose}
      />
      <OverlayBody>
        <div className={styles.supportContent}>
          {/* About section */}
          <div className={styles.aboutSection}>
            <h3 className={styles.sectionTitle}>{s.aboutTitle}</h3>
            <p className={styles.aboutText} dangerouslySetInnerHTML={{ __html: s.aboutText1 }} />
            <p className={styles.aboutText} dangerouslySetInnerHTML={{ __html: s.aboutText2 }} />
          </div>

          {/* Open Source Note */}
          <div className={styles.noteBox}>
            <p className={styles.noteText} dangerouslySetInnerHTML={{ __html: s.noteTitle }} />
          </div>

          {/* Ko-fi Widget */}
          <div className={styles.kofiSection}>
            <iframe
              id="kofiframe"
              src="https://ko-fi.com/sakushipersonaui/?hidefeed=true&widget=true&embed=true&preview=true"
              className={styles.kofiIframe}
              height="712"
              title="sakushipersonaui"
            />
          </div>

          {/* GitHub Star */}
          <div className={styles.starSection}>
            <p className={styles.starText} dangerouslySetInnerHTML={{ __html: s.starText }} />
            <a
              href="https://github.com/Sakushi-Dev/PersonaUI"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.githubLink}
            >
              {s.starBtn}
            </a>
          </div>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>{s.close}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
