// ── InterfaceSettingsOverlay ──
// Dark mode, colors, fonts, dynamic background, notification sound

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import { useTheme } from '../../hooks/useTheme';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Slider from '../../components/Slider/Slider';
import ColorPicker from '../../components/ColorPicker/ColorPicker';
import Button from '../../components/Button/Button';
import InterfacePreview from '../../components/InterfacePreview/InterfacePreview';
import styles from './Overlays.module.css';

const FONT_OPTIONS = [
  { value: 'ubuntu', label: 'Ubuntu' },
  { value: 'comic sans ms', label: 'Comic Sans' },
  { value: 'times new roman', label: 'Times New Roman' },
  { value: 'courier new', label: 'Courier New' },
];

export default function InterfaceSettingsOverlay({ open, onClose }) {
  const { get, setMany } = useSettings();
  const { isDark: themeIsDark, colors: themeColors, setIsDark, updateColors, setFontSize: setThemeFontSize, setFontFamily: setThemeFontFamily, setDynamicBackground: setThemeDynBg } = useTheme();

  // Snapshot of ThemeContext state when overlay opens, for rollback on close
  const [snapshot, setSnapshot] = useState(null);

  const [darkMode, setDarkMode] = useState(false);
  const [dynamicBg, setDynamicBg] = useState(true);
  const [notificationSound, setNotificationSound] = useState(false);
  const [bgColor, setBgColor] = useState('#ffffff');
  const [gradient1, setGradient1] = useState('#89CFF0');
  const [color2, setColor2] = useState('#a8d5ff');
  const [nonverbalColor, setNonverbalColor] = useState('#e4ba00');
  const [fontSize, setFontSize] = useState(18);
  const [fontFamily, setFontFamily] = useState('ubuntu');

  useEffect(() => {
    if (open) {
      // Take snapshot for rollback
      setSnapshot({ isDark: themeIsDark, colors: { ...themeColors } });

      const dm = get('darkMode', false);
      setDarkMode(dm);
      setDynamicBg(get('dynamicBackground', true));
      setNotificationSound(get('notificationSound', false));
      setBgColor(dm ? get('backgroundColor_dark', '#1a2332') : get('backgroundColor_light', '#d7dce4'));
      setGradient1(dm ? get('colorGradient1_dark', '#2a3f5f') : get('colorGradient1_light', '#66cfff'));
      setColor2(dm ? get('color2_dark', '#3d4f66') : get('color2_light', '#fd91ee'));
      setNonverbalColor(get('nonverbalColor', '#e4ba00'));
      setFontSize(parseInt(get('bubbleFontSize', '18'), 10));
      setFontFamily(get('bubbleFontFamily', 'ubuntu'));
    }
  }, [open, get, themeIsDark, themeColors]);

  // ── Dark mode toggle handler: swap color pickers to new mode ──
  const handleDarkModeChange = useCallback((checked) => {
    // Store current mode's colors locally before switching
    const newSuffix = checked ? '_dark' : '_light';
    const defaults = checked
      ? { bg: '#1a2332', g1: '#2a3f5f', c2: '#3d4f66' }
      : { bg: '#d7dce4', g1: '#66cfff', c2: '#fd91ee' };

    // Load colors for the new mode from saved settings
    setBgColor(get(`backgroundColor${newSuffix}`, defaults.bg));
    setGradient1(get(`colorGradient1${newSuffix}`, defaults.g1));
    setColor2(get(`color2${newSuffix}`, defaults.c2));
    setDarkMode(checked);
  }, [get]);

  // ── No live preview to chat — only InterfacePreview shows changes via props ──

  const handleSave = useCallback(() => {
    const suffix = darkMode ? '_dark' : '_light';
    const otherSuffix = darkMode ? '_light' : '_dark';

    // Persist to server settings
    setMany({
      darkMode,
      dynamicBackground: dynamicBg,
      notificationSound,
      [`backgroundColor${suffix}`]: bgColor,
      [`colorGradient1${suffix}`]: gradient1,
      [`color2${suffix}`]: color2,
      [`backgroundColor${otherSuffix}`]: get(`backgroundColor${otherSuffix}`),
      [`colorGradient1${otherSuffix}`]: get(`colorGradient1${otherSuffix}`),
      [`color2${otherSuffix}`]: get(`color2${otherSuffix}`),
      nonverbalColor,
      bubbleFontSize: String(fontSize),
      bubbleFontFamily: fontFamily,
    });

    // Apply to ThemeContext (this updates the actual chat UI)
    setIsDark(darkMode);
    updateColors({
      [`backgroundColor${suffix}`]: bgColor,
      [`colorGradient1${suffix}`]: gradient1,
      [`color2${suffix}`]: color2,
      nonverbalColor,
    });
    setThemeFontSize(fontSize);
    setThemeFontFamily(fontFamily);
    setThemeDynBg(dynamicBg);

    setSnapshot(null);
    onClose();
  }, [darkMode, dynamicBg, notificationSound, bgColor, gradient1, color2, nonverbalColor, fontSize, fontFamily, get, setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeDynBg, onClose]);

  // ── Close without saving: rollback ThemeContext to snapshot ──
  const handleClose = useCallback(() => {
    // No rollback needed — we never touched ThemeContext during editing
    setSnapshot(null);
    onClose();
  }, [onClose]);

  const handleReset = useCallback(() => {
    setDarkMode(false);
    setDynamicBg(true);
    setNotificationSound(false);
    setBgColor('#d7dce4');
    setGradient1('#66cfff');
    setColor2('#fd91ee');
    setNonverbalColor('#e4ba00');
    setFontSize(18);
    setFontFamily('ubuntu');
  }, []);

  return (
    <Overlay open={open} onClose={handleClose} width="520px">
      <OverlayHeader title="Interface-Einstellungen" onClose={handleClose} />
      <OverlayBody>
        <div style={{ marginBottom: 16 }}>
          <InterfacePreview
            isDark={darkMode}
            nonverbalColor={nonverbalColor}
            bgColor={bgColor}
            gradient1={gradient1}
            gradient2={color2}
            dynamicBg={dynamicBg}
            fontSize={fontSize}
            fontFamily={fontFamily}
          />
        </div>

        <div className={styles.settingRow}>
          <Toggle
            label={darkMode ? 'Dunkel' : 'Hell'}
            checked={darkMode}
            onChange={handleDarkModeChange}
            id="dark-mode"
          />
        </div>

        <div className={styles.settingRow}>
          <Toggle
            label={dynamicBg ? 'Aktiv' : 'Inaktiv'}
            checked={dynamicBg}
            onChange={setDynamicBg}
            id="dynamic-bg"
          />
          <span className={styles.settingLabel}>Dynamischer Hintergrund</span>
        </div>

        <div className={styles.settingRow}>
          <Toggle
            label={notificationSound ? 'An' : 'Aus'}
            checked={notificationSound}
            onChange={setNotificationSound}
            id="notification-sound"
          />
          <span className={styles.settingLabel}>Benachrichtigungston</span>
        </div>

        <div className={styles.colorGrid}>
          <ColorPicker label="Hintergrund" value={bgColor} onChange={setBgColor} />
          <ColorPicker label="Gradient 1" value={gradient1} onChange={setGradient1} />
          <ColorPicker label="Gradient 2" value={color2} onChange={setColor2} />
          <ColorPicker label="Nonverbal" value={nonverbalColor} onChange={setNonverbalColor} />
        </div>

        <Slider
          label="Schriftgröße"
          value={fontSize}
          onChange={(v) => setFontSize(Math.round(v))}
          min={14}
          max={28}
          step={1}
          displayValue={`${fontSize}px`}
        />

        <div className={styles.fontSelector}>
          <p className={styles.settingLabel}>Schriftart</p>
          <div className={styles.radioGroup}>
            {FONT_OPTIONS.map((f) => (
              <label key={f.value} className={styles.radioLabel}>
                <input
                  type="radio"
                  name="font-family"
                  value={f.value}
                  checked={fontFamily === f.value}
                  onChange={() => setFontFamily(f.value)}
                />
                <span style={{ fontFamily: f.value }}>{f.label}</span>
              </label>
            ))}
          </div>
        </div>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={handleReset}>Zurücksetzen</Button>
        <Button variant="primary" onClick={handleSave}>Speichern</Button>
      </OverlayFooter>
    </Overlay>
  );
}
