// ── SupportOverlay ──
// Ko-fi support overlay with project info

import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import { HeartIcon } from '../../components/Icons/Icons';
import styles from './SupportOverlay.module.css';

export default function SupportOverlay({ open, onClose }) {
  return (
    <Overlay open={open} onClose={onClose} width="480px">
      <OverlayHeader
        title="Projekt unterstützen"
        icon={<HeartIcon size={20} />}
        onClose={onClose}
      />
      <OverlayBody>
        <div className={styles.supportContent}>
          {/* About section */}
          <div className={styles.aboutSection}>
            <h3 className={styles.sectionTitle}>Über PersonaUI</h3>
            <p className={styles.aboutText}>
              PersonaUI ist ein leidenschaftliches Solo-Projekt von <strong>Sakushi</strong> — 
              ein Open-Source AI-Companion, der komplett lokal läuft, deine Daten respektiert 
              und dir einzigartige Persona-Erlebnisse bietet.
            </p>
            <p className={styles.aboutText}>
              Mein Ziel ist es, PersonaUI kontinuierlich weiterzuentwickeln — mit besseren 
              Personas, intelligentem Gedächtnis (Cortex), und einer UI, die sich wie eine 
              echte Unterhaltung anfühlt. Jede Unterstützung hilft mir, mehr Zeit in dieses 
              Projekt zu investieren.
            </p>
          </div>

          {/* Open Source Note */}
          <div className={styles.noteBox}>
            <p className={styles.noteText}>
              <strong>Ein Wort zur Transparenz:</strong> PersonaUI ist und bleibt Open Source 
              und kostenlos. Diese Option existiert nur für diejenigen, die das Projekt 
              freiwillig unterstützen möchten — keine Features werden dadurch freigeschaltet, 
              keine Inhalte zurückgehalten. Versprochen. 🤝
            </p>
          </div>

          {/* Ko-fi Section */}
          <div className={styles.kofiSection}>
            <div className={styles.kofiIcon}>☕</div>
            <p className={styles.kofiText}>
              Wenn dir PersonaUI gefällt, kannst du mir einen Kaffee spendieren:
            </p>
            <a
              href="https://ko-fi.com/sakushipersona"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.kofiButton}
            >
              <span className={styles.kofiEmoji}>☕</span>
              Support auf Ko-fi
            </a>
          </div>

          {/* GitHub Star */}
          <div className={styles.starSection}>
            <p className={styles.starText}>
              Du kannst das Projekt auch unterstützen, indem du einen <strong>⭐ Star</strong> auf GitHub hinterlässt:
            </p>
            <a
              href="https://github.com/Sakushi-Dev/PersonaUI"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.githubLink}
            >
              ⭐ PersonaUI auf GitHub
            </a>
          </div>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
      </OverlayFooter>
    </Overlay>
  );
}
