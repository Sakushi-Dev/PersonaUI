// ── ApiWarningOverlay ──
// Shown when no API key is configured

import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { WarningIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function ApiWarningOverlay({ open, onClose, onOpenApiKey }) {
  const { t } = useLanguage();
  const s = t('apiWarning');
  const sc = t('common');

  return (
    <Overlay open={open} onClose={onClose} width="420px">
      <OverlayHeader title={s.title} icon={<WarningIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        <div className={styles.infoContent}>
          <p>{s.text}</p>
          <ol className={styles.stepList}>
            <li dangerouslySetInnerHTML={{ __html: s.step1 }} />
            <li>{s.step2}</li>
            <li>{s.step3}</li>
          </ol>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>{sc.close}</Button>
        <Button variant="primary" onClick={() => { onClose(); onOpenApiKey?.(); }}>
          {s.setupBtn}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
