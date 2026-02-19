// ── InterfaceSettingsOverlay ──
// Dark mode, colors, fonts, dynamic background, notification sound
// Logic mirrors legacy SettingsManager: openInterfaceSettings / saveInterfaceSettings / resetInterfaceSettings

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import { useTheme } from '../../hooks/useTheme';
import { resolveFontFamily, FONT_FAMILY_MAP } from '../../utils/constants';
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

// Font options – values are shorthand keys matching legacy radio values
const FONT_OPTIONS = [
  { value: 'ubuntu', label: 'Ubuntu (Standard)' },
  { value: 'comic', label: 'Comic Sans' },
  { value: 'times', label: 'Times New Roman' },
  { value: 'courier', label: 'Courier New' },
];

// Color defaults matching legacy resetInterfaceSettings exactly
const DEFAULT_COLORS = {
  light: { bg: '#a3baff', g1: '#66cfff', c2: '#fd91ee' },
  dark:  { bg: '#1a2332', g1: '#2a3f5f', c2: '#3d4f66' },
};

export default function InterfaceSettingsOverlay({ open, onClose }) {
  const { get, setMany } = useSettings();
  const {
    setIsDark,
    updateColors,
    setFontSize: setThemeFontSize,
    setFontFamily: setThemeFontFamily,
    setDynamicBackground: setThemeDynBg,
  } = useTheme();

  const [darkMode, setDarkMode] = useState(false);
  const [dynamicBg, setDynamicBg] = useState(true);
  const [notificationSound, setNotificationSound] = useState(true);
  const [bgColor, setBgColor] = useState('#a3baff');
  const [gradient1, setGradient1] = useState('#66cfff');
  const [color2, setColor2] = useState('#fd91ee');
  const [nonverbalColor, setNonverbalColor] = useState('#e4ba00');
  const [fontSize, setFontSize] = useState(18);
  const [fontFamily, setFontFamily] = useState('ubuntu');

  // ── Load settings when overlay opens (mirrors legacy openInterfaceSettings) ──
  useEffect(() => {
    if (!open) return;

    const dm = get('darkMode', false);
    const mode = dm ? 'dark' : 'light';
    const defs = DEFAULT_COLORS[mode];

    setDarkMode(dm);
    setDynamicBg(get('dynamicBackground', true));
    setNotificationSound(get('notificationSound', true));
    setBgColor(get(`backgroundColor_${mode}`, defs.bg));
    setGradient1(get(`colorGradient1_${mode}`, defs.g1));
    setColor2(get(`color2_${mode}`, defs.c2));
    setNonverbalColor(get('nonverbalColor', '#e4ba00'));
    setFontSize(parseInt(get('bubbleFontSize', '18'), 10));
    setFontFamily(get('bubbleFontFamily', 'ubuntu'));
  }, [open, get]);

  // ── Dark mode toggle: load colors for the new mode (mirrors legacy setupToggleSync) ──
  const handleDarkModeChange = useCallback((checked) => {
    const mode = checked ? 'dark' : 'light';
    const defs = DEFAULT_COLORS[mode];

    setBgColor(get(`backgroundColor_${mode}`, defs.bg));
    setGradient1(get(`colorGradient1_${mode}`, defs.g1));
    setColor2(get(`color2_${mode}`, defs.c2));
    setDarkMode(checked);
  }, [get]);

  // ── Save (mirrors legacy saveInterfaceSettings) ──
  const handleSave = useCallback(() => {
    const mode = darkMode ? 'dark' : 'light';
    const otherMode = darkMode ? 'light' : 'dark';

    // Persist ALL settings to server
    setMany({
      darkMode,
      dynamicBackground: dynamicBg,
      notificationSound,
      [`backgroundColor_${mode}`]: bgColor,
      [`colorGradient1_${mode}`]: gradient1,
      [`color2_${mode}`]: color2,
      // Preserve the other mode's colors unchanged
      [`backgroundColor_${otherMode}`]: get(`backgroundColor_${otherMode}`),
      [`colorGradient1_${otherMode}`]: get(`colorGradient1_${otherMode}`),
      [`color2_${otherMode}`]: get(`color2_${otherMode}`),
      nonverbalColor,
      bubbleFontSize: String(fontSize),
      bubbleFontFamily: fontFamily,
    });

    // Apply to ThemeContext (live UI update)
    setIsDark(darkMode);
    updateColors({
      [`backgroundColor_${mode}`]: bgColor,
      [`colorGradient1_${mode}`]: gradient1,
      [`color2_${mode}`]: color2,
      nonverbalColor,
    });
    setThemeFontSize(fontSize);
    setThemeFontFamily(resolveFontFamily(fontFamily));
    setThemeDynBg(dynamicBg);

    onClose();
  }, [darkMode, dynamicBg, notificationSound, bgColor, gradient1, color2, nonverbalColor, fontSize, fontFamily, get, setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeDynBg, onClose]);

  // ── Close without saving ──
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // ── Reset (mirrors legacy resetInterfaceSettings exactly) ──
  const handleReset = useCallback(() => {
    if (!window.confirm('Möchtest du die Interface-Einstellungen auf die Standardwerte zurücksetzen?')) {
      return;
    }

    const defLight = DEFAULT_COLORS.light;
    const defDark  = DEFAULT_COLORS.dark;

    // 1) Persist ALL defaults to server (both modes) — matches legacy apply* calls
    setMany({
      darkMode: false,
      dynamicBackground: true,
      notificationSound: true,
      backgroundColor_light: defLight.bg,
      colorGradient1_light: defLight.g1,
      color2_light: defLight.c2,
      backgroundColor_dark: defDark.bg,
      colorGradient1_dark: defDark.g1,
      color2_dark: defDark.c2,
      nonverbalColor: '#e4ba00',
      bubbleFontSize: '18',
      bubbleFontFamily: 'ubuntu',
    });

    // 2) Apply defaults to ThemeContext (live UI update) — matches legacy applyCurrentModeColors etc.
    setIsDark(false);
    updateColors({
      backgroundColor_light: defLight.bg,
      colorGradient1_light: defLight.g1,
      color2_light: defLight.c2,
      backgroundColor_dark: defDark.bg,
      colorGradient1_dark: defDark.g1,
      color2_dark: defDark.c2,
      nonverbalColor: '#e4ba00',
    });
    setThemeFontSize(18);
    setThemeFontFamily(resolveFontFamily('ubuntu'));
    setThemeDynBg(true);

    // 3) Update local form state (light mode colors shown since darkMode = false)
    setDarkMode(false);
    setDynamicBg(true);
    setNotificationSound(true);
    setBgColor(defLight.bg);
    setGradient1(defLight.g1);
    setColor2(defLight.c2);
    setNonverbalColor('#e4ba00');
    setFontSize(18);
    setFontFamily('ubuntu');
  }, [setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeDynBg]);

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

        {/* Design-Modus (legacy: dark-mode-toggle) */}
        <div className={styles.settingRow}>
          <Toggle
            label={darkMode ? 'Dunkel' : 'Hell'}
            checked={darkMode}
            onChange={handleDarkModeChange}
            id="dark-mode"
          />
          <span className={styles.settingLabel}>Design-Modus</span>
        </div>

        {/* Dynamischer Hintergrund (legacy: dynamic-bg-toggle) */}
        <div className={styles.settingRow}>
          <Toggle
            label={dynamicBg ? 'Aktiv' : 'Inaktiv'}
            checked={dynamicBg}
            onChange={setDynamicBg}
            id="dynamic-bg"
          />
          <span className={styles.settingLabel}>Dynamischer Hintergrund</span>
        </div>

        {/* Benachrichtigungston */}
        <div className={styles.settingRow}>
          <Toggle
            label={notificationSound ? 'An' : 'Aus'}
            checked={notificationSound}
            onChange={setNotificationSound}
            id="notification-sound"
          />
          <span className={styles.settingLabel}>Benachrichtigungston</span>
        </div>

        {/* Color pickers (legacy: background-color, color-gradient1, color-2, nonverbal-color) */}
        <div className={styles.colorGrid}>
          <ColorPicker label="Hintergrundfarbe" value={bgColor} onChange={setBgColor} />
          <ColorPicker label="Verlaufsfarbe 1" value={gradient1} onChange={setGradient1} />
          <ColorPicker label="Verlaufsfarbe 2" value={color2} onChange={setColor2} />
          <ColorPicker label="Nonverbale Text-Farbe" value={nonverbalColor} onChange={setNonverbalColor} />
        </div>

        {/* Font size slider (legacy: bubble-font-size, 14-28) */}
        <Slider
          label="Chat-Nachricht Schriftgröße"
          value={fontSize}
          onChange={(v) => setFontSize(Math.round(v))}
          min={14}
          max={28}
          step={1}
          displayValue={`${fontSize}px`}
        />

        {/* Font family radios (legacy: bubble-font-family) */}
        <div className={styles.fontSelector}>
          <p className={styles.settingLabel}>Chat-Nachricht Schriftart</p>
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
                <span style={{ fontFamily: resolveFontFamily(f.value) }}>{f.label}</span>
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
