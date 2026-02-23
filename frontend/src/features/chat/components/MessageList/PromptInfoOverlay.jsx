// ── PromptInfoOverlay ──
// Full token breakdown matching the legacy overlay

import { useMemo, useRef } from 'react';
import { useSettings } from '../../../../hooks/useSettings';
import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './PromptInfoOverlay.module.css';

export default function PromptInfoOverlay({ open, onClose, stats }) {
  const { get, defaults } = useSettings();
  const { t } = useLanguage();
  const s = t('promptInfo');

  if (!open || !stats) return null;

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
  const modelDisplayName = modelMeta?.pricingName || modelMeta?.label || currentModel || s.unknown;

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
            <h3>{s.title}</h3>
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
            <span className={styles.progressLabelCenter}>{grandTotal.toLocaleString()} {s.tokens}</span>
            <span className={styles.progressLabelSide}>50k</span>
          </div>
          <div className={styles.costInfo}>
            ~ ${totalCost.toFixed(6)} (Input: ${inputCost.toFixed(6)} | Output: ${outputCost.toFixed(6)})
          </div>
          <div className={styles.costDisclaimer}>
            {s.costDisclaimer
              .replace('{model}', modelDisplayName)
              .replace('{inputPrice}', String(inputPrice))
              .replace('{outputPrice}', String(outputPrice))}
          </div>
        </div>

        {/* Stats sections */}
        <div className={styles.stats}>
          {/* System Prompt */}
          <div className={`${styles.section} ${styles.systemPrompt}`}>
            <div className={styles.sectionLabel}><span className={styles.dot} />{s.systemPrompt}</div>
            <div className={styles.breakdown}>
              <div className={styles.statItem}>
                <span className={styles.statName}>{s.promptPersona}</span>
                <span className={styles.statValue}>{systemScaled.toLocaleString()} {s.token}</span>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className={`${styles.section} ${styles.history}`}>
            <div className={styles.sectionLabel}><span className={styles.dot} />{s.messages}</div>
            <div className={styles.breakdown}>
              <div className={styles.statItem}>
                <span className={styles.statName}>{s.chatHistory}</span>
                <span className={styles.statValue}>{historyScaled.toLocaleString()} {s.token}</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statName}>{s.userMessage}</span>
                <span className={styles.statValue}>{userMsgScaled.toLocaleString()} {s.token}</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statName}>{s.prefill}</span>
                <span className={styles.statValue}>{prefillScaled.toLocaleString()} {s.token}</span>
              </div>
            </div>
          </div>

          {/* Total */}
          <div className={`${styles.section} ${styles.total}`}>
            <div className={styles.sectionLabel}><span className={styles.dot} />{s.totalApi}</div>
            <div className={styles.breakdown}>
              <div className={styles.statItem}>
                <span className={styles.statName}>{s.input}</span>
                <span className={styles.statValue}>{apiInput.toLocaleString()} {s.token}</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statName}>{s.output}</span>
                <span className={styles.statValue}>{outputTokens.toLocaleString()} {s.token}</span>
              </div>
              <div className={`${styles.statItem} ${styles.statSum}`}>
                <span className={styles.statName}>{s.total}</span>
                <span className={styles.statValue}>{grandTotal.toLocaleString()} {s.token}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
