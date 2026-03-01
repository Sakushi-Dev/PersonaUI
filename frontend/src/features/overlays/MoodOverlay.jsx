// ── MoodOverlay ──
// Mood visualization and settings in a tabbed overlay

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSession } from '../../hooks/useSession';
import { useSettings } from '../../hooks/useSettings';
import { useLanguage } from '../../hooks/useLanguage';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getCurrentMood, getMoodHistory, updateMoodSettings, resetMood } from '../../services/moodApi';
import styles from './Overlays.module.css';

// ── Tab keys ──
const TAB_KEYS = [
  { key: 'current', label: 'Current State' },
  { key: 'history', label: 'History' },
  { key: 'settings', label: 'Settings' },
];

export default function MoodOverlay({ open, onClose, panelOnly }) {
  const { personaId } = useSession();
  const { get, setMany } = useSettings();
  const { t } = useLanguage();
  const sc = t('common');

  const TABS = TAB_KEYS;

  // ── Settings State ──
  const [moodEnabled, setMoodEnabled] = useState(true);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [decayRate, setDecayRate] = useState(0.1);

  // ── Mood State ──
  const [currentMood, setCurrentMood] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('current');

  // ── Loading / Error ──
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // ══════════════════════════════════════════
  // Load settings + mood data when overlay opens
  // ══════════════════════════════════════════
  useEffect(() => {
    if (!open) return;

    // Sync settings into local state
    setMoodEnabled(get('moodEnabled', true));
    setSensitivity(get('moodSensitivity', 0.5));
    setDecayRate(get('moodDecayRate', 0.1));

    // Reset UI state
    setActiveTab('current');
    setError(null);

    loadMoodData();
  }, [open, get]);

  // ── Load current mood data ──
  const loadMoodData = useCallback(async () => {
    if (!personaId) return;

    setLoading(true);
    try {
      const response = await getCurrentMood();
      if (response.enabled) {
        setCurrentMood(response.mood);
      } else {
        setCurrentMood(null);
      }
    } catch (err) {
      console.error('Failed to load mood data:', err);
      setError(err.message || 'Failed to load mood data');
    }
    setLoading(false);
  }, [personaId]);

  // ── Load mood history ──
  const loadHistory = useCallback(async () => {
    if (!personaId) return;

    try {
      const response = await getMoodHistory(50);
      if (response.enabled) {
        setHistory(response.history || []);
      }
    } catch (err) {
      console.error('Failed to load mood history:', err);
    }
  }, [personaId]);

  // ── Listen for live mood updates ──
  useEffect(() => {
    const handleMoodUpdate = (event) => {
      setCurrentMood(event.detail);
    };

    if (open) {
      window.addEventListener('mood-update', handleMoodUpdate);
      return () => window.removeEventListener('mood-update', handleMoodUpdate);
    }
  }, [open]);

  // ── Load history when switching to history tab ──
  useEffect(() => {
    if (activeTab === 'history' && open) {
      loadHistory();
    }
  }, [activeTab, open, loadHistory]);

  // ── Save settings ──
  const handleSaveSettings = useCallback(async () => {
    setSaving(true);
    try {
      // Update mood-specific settings via API
      await updateMoodSettings({
        sensitivity: sensitivity,
        decay_rate: decayRate,
      });

      // Update enabled state via settings system
      await setMany({ moodEnabled });

      // Reload mood data if enabled state changed
      if (moodEnabled) {
        loadMoodData();
      }
    } catch (err) {
      console.error('Failed to save settings:', err);
      setError(err.message || 'Failed to save settings');
    }
    setSaving(false);
  }, [sensitivity, decayRate, moodEnabled, setMany, loadMoodData]);

  // ── Reset mood ──
  const handleResetMood = useCallback(async () => {
    if (!confirm('Reset mood to baseline values?')) return;

    setSaving(true);
    try {
      const response = await resetMood();
      if (response.enabled) {
        setCurrentMood(response.mood);
      }
    } catch (err) {
      console.error('Failed to reset mood:', err);
      setError(err.message || 'Failed to reset mood');
    }
    setSaving(false);
  }, []);

  // ── Render radar chart ──
  const renderRadarChart = () => {
    if (!currentMood) return null;

    const { anger, sadness, affection, arousal, trust } = currentMood;
    const values = [anger, sadness, affection, arousal, trust];
    const labels = ['Anger', 'Sadness', 'Affection', 'Arousal', 'Trust'];
    
    // SVG dimensions
    const size = 200;
    const center = size / 2;
    const maxRadius = center - 40;
    
    // Calculate vertex positions (pentagon)
    const vertices = labels.map((_, i) => {
      const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2; // Start at top
      return {
        x: center + maxRadius * Math.cos(angle),
        y: center + maxRadius * Math.sin(angle),
        label: labels[i],
      };
    });

    // Calculate data polygon points
    const dataPoints = values.map((value, i) => {
      const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
      const radius = (value / 100) * maxRadius;
      return {
        x: center + radius * Math.cos(angle),
        y: center + radius * Math.sin(angle),
      };
    });

    const dataPolygonPoints = dataPoints.map(p => `${p.x},${p.y}`).join(' ');

    // Grid polygons (33%, 66%, 100%)
    const gridLevels = [0.33, 0.66, 1.0];
    const gridPolygons = gridLevels.map(level => {
      const points = vertices.map(v => {
        const x = center + (v.x - center) * level;
        const y = center + (v.y - center) * level;
        return `${x},${y}`;
      }).join(' ');
      return points;
    });

    return (
      <div className={styles.radarContainer}>
        <svg viewBox={`0 0 ${size} ${size}`} className={styles.radar}>
          {/* Grid polygons */}
          {gridPolygons.map((points, i) => (
            <polygon
              key={i}
              points={points}
              className={styles.radarGrid}
            />
          ))}
          
          {/* Axis lines */}
          {vertices.map((vertex, i) => (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={vertex.x}
              y2={vertex.y}
              className={styles.radarAxis}
            />
          ))}
          
          {/* Data polygon */}
          <polygon
            points={dataPolygonPoints}
            className={styles.radarData}
          />
          
          {/* Labels */}
          {vertices.map((vertex, i) => (
            <text
              key={i}
              x={vertex.x + (vertex.x > center ? 10 : vertex.x < center ? -10 : 0)}
              y={vertex.y + (vertex.y > center ? 15 : vertex.y < center ? -5 : -10)}
              className={styles.radarLabel}
              textAnchor={vertex.x > center ? 'start' : vertex.x < center ? 'end' : 'middle'}
            >
              {vertex.label}
            </text>
          ))}
        </svg>
        
        {/* Mood emoji and dominant emotion */}
        <div className={styles.moodSummary}>
          <div className={styles.moodEmoji}>{currentMood.emoji}</div>
          <div className={styles.moodDominant}>
            Dominant: {currentMood.dominant} ({currentMood[currentMood.dominant]}/100)
          </div>
        </div>
      </div>
    );
  };

  // ── Render current tab content ──
  const renderTabContent = () => {
    if (loading) {
      return (
        <div className={styles.loadingContainer}>
          <Spinner />
          <p>Loading mood data...</p>
        </div>
      );
    }

    if (!moodEnabled) {
      return (
        <div className={styles.disabledMessage}>
          <p>Mood system is disabled. Enable it in the Settings tab.</p>
        </div>
      );
    }

    switch (activeTab) {
      case 'current':
        return (
          <div className={styles.currentTab}>
            {currentMood ? (
              <>
                {renderRadarChart()}
                <div className={styles.dimensionsList}>
                  <h4>Current Values:</h4>
                  <div className={styles.dimensionGrid}>
                    <div className={`${styles.dimension} ${currentMood.dominant === 'anger' ? styles.dominant : ''}`}>
                      <span>Anger:</span> <span>{currentMood.anger}/100</span>
                    </div>
                    <div className={`${styles.dimension} ${currentMood.dominant === 'sadness' ? styles.dominant : ''}`}>
                      <span>Sadness:</span> <span>{currentMood.sadness}/100</span>
                    </div>
                    <div className={`${styles.dimension} ${currentMood.dominant === 'affection' ? styles.dominant : ''}`}>
                      <span>Affection:</span> <span>{currentMood.affection}/100</span>
                    </div>
                    <div className={`${styles.dimension} ${currentMood.dominant === 'arousal' ? styles.dominant : ''}`}>
                      <span>Arousal:</span> <span>{currentMood.arousal}/100</span>
                    </div>
                    <div className={`${styles.dimension} ${currentMood.dominant === 'trust' ? styles.dominant : ''}`}>
                      <span>Trust:</span> <span>{currentMood.trust}/100</span>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <p>No mood data available</p>
            )}
          </div>
        );

      case 'history':
        return (
          <div className={styles.historyTab}>
            {history.length > 0 ? (
              <div className={styles.historyList}>
                {history.map((entry, i) => (
                  <div key={i} className={styles.historyEntry}>
                    <div className={styles.historyTimestamp}>
                      {new Date(entry.timestamp).toLocaleString()}
                    </div>
                    <div className={styles.historyValues}>
                      A:{entry.anger} S:{entry.sadness} Af:{entry.affection} Ar:{entry.arousal} T:{entry.trust}
                    </div>
                    {entry.trigger_text && (
                      <div className={styles.historyTrigger}>
                        "{entry.trigger_text.substring(0, 100)}..."
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p>No mood history available</p>
            )}
          </div>
        );

      case 'settings':
        return (
          <div className={styles.settingsTab}>
            <div className={styles.setting}>
              <label>
                <Toggle
                  enabled={moodEnabled}
                  onChange={setMoodEnabled}
                />
                Enable Mood System
              </label>
            </div>

            {moodEnabled && (
              <>
                <div className={styles.setting}>
                  <label>
                    Sensitivity: {sensitivity.toFixed(1)}
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.1"
                      value={sensitivity}
                      onChange={(e) => setSensitivity(parseFloat(e.target.value))}
                      className={styles.slider}
                    />
                  </label>
                  <small>How strongly responses affect mood</small>
                </div>

                <div className={styles.setting}>
                  <label>
                    Decay Rate: {decayRate.toFixed(2)}
                    <input
                      type="range"
                      min="0.05"
                      max="0.5"
                      step="0.05"
                      value={decayRate}
                      onChange={(e) => setDecayRate(parseFloat(e.target.value))}
                      className={styles.slider}
                    />
                  </label>
                  <small>How quickly mood returns to baseline</small>
                </div>

                <div className={styles.setting}>
                  <Button
                    onClick={handleResetMood}
                    disabled={saving}
                    variant="secondary"
                  >
                    Reset Mood to Baseline
                  </Button>
                </div>
              </>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Overlay open={open} onClose={onClose} panelOnly={panelOnly}>
      <OverlayHeader onClose={onClose} panelOnly={panelOnly}>
        Mood System
      </OverlayHeader>

      <OverlayBody>
        {/* Tab Navigation */}
        <div className={styles.tabNav}>
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`${styles.tabButton} ${activeTab === tab.key ? styles.active : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Error Message */}
        {error && (
          <div className={styles.error}>
            {error}
          </div>
        )}

        {/* Tab Content */}
        <div className={styles.tabContent}>
          {renderTabContent()}
        </div>
      </OverlayBody>

      {activeTab === 'settings' && (
        <OverlayFooter>
          <Button
            onClick={handleSaveSettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </OverlayFooter>
      )}
    </Overlay>
  );
}