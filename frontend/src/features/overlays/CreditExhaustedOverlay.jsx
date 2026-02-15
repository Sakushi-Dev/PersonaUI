// ── CreditExhaustedOverlay ──
// Shown when API credits are spent

import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import styles from './Overlays.module.css';

export default function CreditExhaustedOverlay({ open, onClose }) {
  const handleRecharge = () => {
    window.open('https://console.anthropic.com/settings/billing', '_blank');
  };

  return (
    <Overlay open={open} onClose={onClose} width="420px">
      <OverlayHeader title="💳 API-Guthaben erschöpft" onClose={onClose} />
      <OverlayBody>
        <div className={styles.infoContent}>
          <p className={styles.highlight}>
            Dein Anthropic API-Guthaben ist aufgebraucht.
          </p>
          <p>Um weiter chatten zu können:</p>
          <ol className={styles.stepList}>
            <li>Öffne das Anthropic Dashboard</li>
            <li>Gehe zu <strong>Settings → Billing</strong></li>
            <li>Lade dein Guthaben auf</li>
          </ol>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
        <Button variant="primary" onClick={handleRecharge}>
          Guthaben aufladen
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
