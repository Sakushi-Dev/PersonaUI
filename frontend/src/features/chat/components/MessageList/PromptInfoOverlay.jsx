// ── PromptInfoOverlay ──

import Overlay from '../../../../components/Overlay/Overlay';
import OverlayHeader from '../../../../components/Overlay/OverlayHeader';
import OverlayBody from '../../../../components/Overlay/OverlayBody';
import styles from './MessageList.module.css';

export default function PromptInfoOverlay({ open, onClose, stats }) {
  if (!stats) return null;

  return (
    <Overlay open={open} onClose={onClose} width="400px">
      <OverlayHeader title="Prompt Info" onClose={onClose} />
      <OverlayBody>
        <div className={styles.promptInfo}>
          {stats.model && (
            <div className={styles.promptStat}>
              <span>Modell:</span>
              <span>{stats.model}</span>
            </div>
          )}
          {stats.prompt_tokens !== undefined && (
            <div className={styles.promptStat}>
              <span>Prompt Tokens:</span>
              <span>{stats.prompt_tokens}</span>
            </div>
          )}
          {stats.completion_tokens !== undefined && (
            <div className={styles.promptStat}>
              <span>Antwort Tokens:</span>
              <span>{stats.completion_tokens}</span>
            </div>
          )}
          {stats.total_tokens !== undefined && (
            <div className={styles.promptStat}>
              <span>Gesamt Tokens:</span>
              <span>{stats.total_tokens}</span>
            </div>
          )}
        </div>
      </OverlayBody>
    </Overlay>
  );
}
