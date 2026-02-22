// ── PromptInfoOverlay ──
// Full token breakdown matching the legacy overlay

import { useMemo, useRef } from 'react';
import { useSettings } from '../../../../hooks/useSettings';
import styles from './PromptInfoOverlay.module.css';

export default function PromptInfoOverlay({ open, onClose, stats }) {
  if (!open || !stats) return null;

  const { get, defaults } = useSettings();

  // ── Real API values ──
  const apiInput = stats.api_input_tokens || 0;
  const outputTokens = stats.output_tokens || 0;
  const grandTotal = apiInput + outputTokens;

  // ── Estimated breakdown (scale proportionally to real API input) ──
  const systemEst = stats.system_prompt_est || 0;
  const historyEst = stats.history_est || 0;
  const userMsgEst = stats.user_msg_est || 0;
  const prefillEst = stats.prefill_est || 0;
  const totalEst = stats.total_est || 1;

  const scale = apiInput > 0 && totalEst > 0 ? apiInput / totalEst : 1;
  const systemScaled = Math.round(systemEst * scale);
  const historyScaled = Math.round(historyEst * scale);
  const userMsgScaled = Math.round(userMsgEst * scale);
  const prefillScaled = Math.round(prefillEst * scale);

  // ── Model pricing ──
  const currentModel = get('apiModel') || 'claude-sonnet-4-5-20250929';
  const modelOptions = defaults.apiModelOptions ?? [];
  const modelMeta = modelOptions.find((o) => o?.value === currentModel) || null;

  const inputPrice = modelMeta?.inputPrice ?? 0;
  const outputPrice = modelMeta?.outputPrice ?? 0;
  const modelDisplayName = modelMeta?.pricingName || modelMeta?.label || currentModel || 'Unbekannt';

  const inputCost = (apiInput / 1_000_000) * inputPrice;
  const outputCost = (outputTokens / 1_000_000) * outputPrice;
  const totalCost = inputCost + outputCost;

  // ── Progress bar ──
  const minTokens = 1000;
  const maxTokens = 50000;
  const percentage = Math.min(Math.max(((grandTotal - minTokens) / (maxTokens - minTokens)) * 100, 0), 100);

  const barColor = useMemo(() => {
    if (percentage <= 20) return '#34a853';
    const t = (percentage - 20) / 80;
    const r = Math.round(52 + (239 - 52) * t);
    const g = Math.round(168 - (168 - 68) * t);
    const b = Math.round(83 - 83 * t);
    return `rgb(${r}, ${g}, ${b})`;
  }, [percentage]);

  const mouseDownOnBackdrop = useRef(false);

  return (
    <div
      className={styles.overlay}
      onMouseDown={(e) => { mouseDownOnBackdrop.current = e.target === e.currentTarget; }}
      onMouseUp={(e) => { if (mouseDownOnBackdrop.current && e.target === e.currentTarget) onClose(); mouseDownOnBackdrop.current = false; }}
    >
      <div className={styles.content}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            <div className={styles.icon}>📊</div>
            <h3>Prompt Informationen</h3>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Progress bar */}
        <div className={styles.progressSection}>
          <div className={styles.progressBarContainer}>
            <div
              className={styles.progressBarFill}
              style={{ width: `${percentage}%`, background: barColor }}
            />
          </div>
          <div className={styles.progressLabels}>
            <span className={styles.progressLabelSide}>1k</span>
            <span className={styles.progressLabelCenter}>{grandTotal.toLocaleString()} Tokens</span>
            <span className={styles.progressLabelSide}>50k</span>
          </div>
          <div className={styles.costInfo}>
            ~ ${totalCost.toFixed(6)} (Input: ${inputCost.toFixed(6)} | Output: ${outputCost.toFixed(6)})
          </div>
          <div className={styles.costDisclaimer}>
            ⚠️ Ungefähre Berechnung – Die API gibt keine Kosteninformationen zurück. Preise basieren auf {modelDisplayName} (${inputPrice}/M Input, ${outputPrice}/M Output). Bitte mit Anbieter-Rechnung abgleichen.
          </div>
        </div>

        {/* Stats sections */}
        <div className={styles.stats}>
          {/* System Prompt */}
          <div className={`${styles.section} ${styles.systemPrompt}`}>
            <div className={styles.sectionLabel}><span className={styles.dot} />System Prompt</div>
            <div className={styles.breakdown}>
              <div className={styles.statItem}>
                <span className={styles.statName}>Prompt + Persona</span>
                <span className={styles.statValue}>{systemScaled.toLocaleString()} Token</span>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className={`${styles.section} ${styles.history}`}>
            <div className={styles.sectionLabel}><span className={styles.dot} />Messages</div>
            <div className={styles.breakdown}>
              <div className={styles.statItem}>
                <span className={styles.statName}>Chat History</span>
                <span className={styles.statValue}>{historyScaled.toLocaleString()} Token</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statName}>User Nachricht</span>
                <span className={styles.statValue}>{userMsgScaled.toLocaleString()} Token</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statName}>Prefill</span>
                <span className={styles.statValue}>{prefillScaled.toLocaleString()} Token</span>
              </div>
            </div>
          </div>

          {/* Total */}
          <div className={`${styles.section} ${styles.total}`}>
            <div className={styles.sectionLabel}><span className={styles.dot} />Gesamt (Anthropic API)</div>
            <div className={styles.breakdown}>
              <div className={styles.statItem}>
                <span className={styles.statName}>Input</span>
                <span className={styles.statValue}>{apiInput.toLocaleString()} Token</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statName}>Output</span>
                <span className={styles.statValue}>{outputTokens.toLocaleString()} Token</span>
              </div>
              <div className={`${styles.statItem} ${styles.statSum}`}>
                <span className={styles.statName}>Total</span>
                <span className={styles.statValue}>{grandTotal.toLocaleString()} Token</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
