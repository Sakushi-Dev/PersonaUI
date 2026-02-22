// ── CreditExhaustedOverlay ──
// Shown when API credits are spent

import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { CreditCardIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function CreditExhaustedOverlay({ open, onClose }) {
  const { t } = useLanguage();
  const s = t('creditExhausted');
  const sc = t('common');

  const handleRecharge = () => {
    window.open('https://console.anthropic.com/settings/billing', '_blank');
  };

  return (
    <Overlay open={open} onClose={onClose} width="420px">
      <OverlayHeader title={s.title} icon={<CreditCardIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        <div className={styles.infoContent}>
          <p className={styles.highlight}>
            {s.text}
          </p>
          <p>{s.instruction}</p>
          <ol className={styles.stepList}>
            <li>{s.step1}</li>
            <li dangerouslySetInnerHTML={{ __html: s.step2 }} />
            <li>{s.step3}</li>
          </ol>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>{sc.close}</Button>
        <Button variant="primary" onClick={handleRecharge}>
          {s.rechargeBtn}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
