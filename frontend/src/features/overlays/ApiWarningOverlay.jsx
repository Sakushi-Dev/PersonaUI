// ── ApiWarningOverlay ──
// Shown when no API key is configured

import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { WarningIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import styles from './Overlays.module.css';

export default function ApiWarningOverlay({ open, onClose, onOpenApiKey }) {
  return (
    <Overlay open={open} onClose={onClose} width="420px">
      <OverlayHeader title="Kein API-Key konfiguriert" icon={<WarningIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        <div className={styles.infoContent}>
          <p>Um PersonaUI nutzen zu können, benötigst du einen Anthropic API-Key.</p>
          <ol className={styles.stepList}>
            <li>Erstelle ein Konto auf <strong>console.anthropic.com</strong></li>
            <li>Generiere einen API-Key</li>
            <li>Füge ihn in den API-Key Einstellungen ein</li>
          </ol>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
        <Button variant="primary" onClick={() => { onClose(); onOpenApiKey?.(); }}>
          API-Key einrichten
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
