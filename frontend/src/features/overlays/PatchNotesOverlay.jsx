// ── PatchNotesOverlay ──
// User-friendly patch notes with version selector

import { useState, useMemo } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import { PatchNotesIcon } from '../../components/Icons/Icons';
import { useLanguage } from '../../hooks/useLanguage';
import patchData from '../../data/patchNotesData.json';
import styles from './PatchNotesOverlay.module.css';

// ── SVG category icons ──
const svgDefaults = { fill: 'none', stroke: 'currentColor', strokeWidth: '1.8', strokeLinecap: 'round', strokeLinejoin: 'round' };

function StarIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" {...svgDefaults}>
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function ZapIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" {...svgDefaults}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

function BugFixIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" {...svgDefaults}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function PaletteIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" {...svgDefaults}>
      <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
      <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
      <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
      <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
    </svg>
  );
}

function CogIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" {...svgDefaults}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" {...svgDefaults}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

const CATEGORY_ICONS = {
  newFeatures: <StarIcon />,
  improvements: <ZapIcon />,
  bugFixes: <BugFixIcon />,
  ui: <PaletteIcon />,
  technical: <CogIcon />,
};

// versions array — index 0 is the latest
const ALL_VERSIONS = patchData.versions || [];

export default function PatchNotesOverlay({ open, onClose }) {
  const { t, language } = useLanguage();
  const s = t('patchNotes');
  const lang = language || 'en';

  // Default to latest version (first in array)
  const [selectedIdx, setSelectedIdx] = useState(0);

  // Reset to latest when overlay opens
  const handleClose = () => {
    setSelectedIdx(0);
    onClose();
  };

  // Resolve current version data for the active language
  const current = useMemo(() => {
    const ver = ALL_VERSIONS[selectedIdx];
    if (!ver) return null;
    const localized = ver[lang] || ver.en || {};
    return { ...ver, ...localized };
  }, [selectedIdx, lang]);

  const isLatest = selectedIdx === 0;

  return (
    <Overlay open={open} onClose={handleClose} width="560px">
      <OverlayHeader
        title={s.title || 'Patch Notes'}
        icon={<PatchNotesIcon size={20} />}
        onClose={handleClose}
      />
      <OverlayBody>
        <div className={styles.patchNotesContent}>
          {/* ── Version selector row ── */}
          <div className={styles.versionRow}>
            <div className={styles.versionSelectWrap}>
              <label className={styles.versionLabel}>{s.versionLabel || 'Version'}</label>
              <div className={styles.selectContainer}>
                <select
                  className={styles.versionSelect}
                  value={selectedIdx}
                  onChange={(e) => setSelectedIdx(Number(e.target.value))}
                >
                  {ALL_VERSIONS.map((v, i) => (
                    <option key={v.id} value={i}>
                      {v.label}{i === 0 ? ` (${s.latestBadge || 'Latest'})` : ''}
                    </option>
                  ))}
                </select>
                <span className={styles.selectChevron}><ChevronDownIcon /></span>
              </div>
            </div>
            {current?.date && (
              <span className={styles.versionDate}>{current.date}</span>
            )}
            {isLatest && (
              <span className={styles.latestBadge}>{s.latestBadge || 'Latest'}</span>
            )}
          </div>

          {/* ── Subtitle / description ── */}
          {current?.subtitle && (
            <p className={styles.subtitle}>{current.subtitle}</p>
          )}

          {/* ── Category sections ── */}
          {current?.categories && Object.entries(current.categories).map(([key, category]) => (
            <div key={key} className={styles.categorySection}>
              <div className={styles.categoryHeader}>
                <span className={styles.categoryIcon}>{CATEGORY_ICONS[key] || null}</span>
                <h3 className={styles.categoryTitle}>{category.title}</h3>
              </div>
              <ul className={styles.notesList}>
                {(category.items || []).map((item, i) => (
                  <li key={i} className={styles.noteItem}>
                    <span className={styles.noteBullet}>›</span>
                    <span className={styles.noteText}>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {/* ── Info note ── */}
          {current?.infoNote && (
            <div className={styles.infoBox}>
              <p className={styles.infoText}>{current.infoNote}</p>
            </div>
          )}
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleClose}>{s.close || 'Close'}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
