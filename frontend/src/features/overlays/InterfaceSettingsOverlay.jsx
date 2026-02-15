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
import styles from './Overlays.module.css';

const FONT_OPTIONS = [
  { value: 'ubuntu', label: 'Ubuntu' },
  { value: 'comic sans ms', label: 'Comic Sans' },
  { value: 'times new roman', label: 'Times New Roman' },
  { value: 'courier new', label: 'Courier New' },
];

export default function InterfaceSettingsOverlay({ open, onClose }) {
  const { get, setMany } = useSettings();
  const { isDark, setIsDark, updateColors, setFontSize: setThemeFontSize, setFontFamily: setThemeFontFamily, setDynamicBackground: setThemeDynBg } = useTheme();

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
      const dm = get('darkMode', false);
      setDarkMode(dm);
      setDynamicBg(get('dynamicBackground', true));
      setNotificationSound(get('notificationSound', false));
      setBgColor(dm ? get('backgroundColor_dark', '#1a2332') : get('backgroundColor_light', '#a3baff'));
      setGradient1(dm ? get('colorGradient1_dark', '#2a3f5f') : get('colorGradient1_light', '#66cfff'));
      setColor2(dm ? get('color2_dark', '#3d4f66') : get('color2_light', '#fd91ee'));
      setNonverbalColor(get('nonverbalColor', '#e4ba00'));
      setFontSize(parseInt(get('bubbleFontSize', '18'), 10));
      setFontFamily(get('bubbleFontFamily', 'ubuntu'));
    }
  }, [open, get]);

  // ── Live preview: apply changes to actual page in real-time ──
  useEffect(() => {
    if (!open) return;
    setIsDark(darkMode);
  }, [darkMode, open, setIsDark]);

  useEffect(() => {
    if (!open) return;
    const suffix = darkMode ? '_dark' : '_light';
    updateColors({
      [`backgroundColor${suffix}`]: bgColor,
      [`colorGradient1${suffix}`]: gradient1,
      [`color2${suffix}`]: color2,
      nonverbalColor,
    });
  }, [bgColor, gradient1, color2, nonverbalColor, darkMode, open, updateColors]);

  useEffect(() => {
    if (!open) return;
    setThemeFontSize(fontSize);
  }, [fontSize, open, setThemeFontSize]);

  useEffect(() => {
    if (!open) return;
    setThemeFontFamily(fontFamily);
  }, [fontFamily, open, setThemeFontFamily]);

  useEffect(() => {
    if (!open) return;
    setThemeDynBg(dynamicBg);
  }, [dynamicBg, open, setThemeDynBg]);

  const handleSave = useCallback(() => {
    const suffix = darkMode ? '_dark' : '_light';
    setMany({
      darkMode,
      dynamicBackground: dynamicBg,
      notificationSound,
      [`backgroundColor${suffix}`]: bgColor,
      [`colorGradient1${suffix}`]: gradient1,
      [`color2${suffix}`]: color2,
      nonverbalColor,
      bubbleFontSize: String(fontSize),
      bubbleFontFamily: fontFamily,
    });
    onClose();
  }, [darkMode, dynamicBg, notificationSound, bgColor, gradient1, color2, nonverbalColor, fontSize, fontFamily, setMany, onClose]);

  const handleReset = useCallback(() => {
    setDarkMode(false);
    setDynamicBg(true);
    setNotificationSound(false);
    setBgColor('#a3baff');
    setGradient1('#66cfff');
    setColor2('#fd91ee');
    setNonverbalColor('#e4ba00');
    setFontSize(18);
    setFontFamily('ubuntu');
  }, []);

  return (
    <Overlay open={open} onClose={onClose} width="520px">
      <OverlayHeader title="Interface-Einstellungen" onClose={onClose} />
      <OverlayBody>
        <div className={styles.settingRow}>
          <Toggle
            label={darkMode ? 'Dunkel' : 'Hell'}
            checked={darkMode}
            onChange={setDarkMode}
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
