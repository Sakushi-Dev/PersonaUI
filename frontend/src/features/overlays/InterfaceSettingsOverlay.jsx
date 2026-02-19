// ── InterfaceSettingsOverlay ──
// Structured into: Preview → Darstellung → Farben → Schrift

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '../../hooks/useSettings';
import { useTheme } from '../../hooks/useTheme';
import { resolveFontFamily, adjustedFontSize, hueToColors, DEFAULT_HUE, NONVERBAL_PRESETS } from '../../utils/constants';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Slider from '../../components/Slider/Slider';
import Button from '../../components/Button/Button';
import InterfacePreview from '../../components/InterfacePreview/InterfacePreview';
import styles from './Overlays.module.css';

// Font options with icons for visual clarity
const FONT_OPTIONS = [
  { value: 'ubuntu',  label: 'Ubuntu',          desc: 'Standard', icon: 'Aa' },
  { value: 'comic',   label: 'Comic Sans',      desc: 'Verspielt', icon: 'Aa' },
  { value: 'times',   label: 'Times New Roman',  desc: 'Klassisch', icon: 'Aa' },
  { value: 'courier', label: 'Courier New',      desc: 'Monospace', icon: 'Aa' },
  { value: 'pixel',   label: 'Pixel',            desc: 'Retro', icon: 'Px' },
  { value: 'console', label: 'Console',          desc: 'Terminal', icon: '>' },
];

export default function InterfaceSettingsOverlay({ open, onClose }) {
  const { get, setMany } = useSettings();
  const {
    setIsDark,
    updateColors,
    setFontSize: setThemeFontSize,
    setFontFamily: setThemeFontFamily,
    setFontKey: setThemeFontKey,
    setDynamicBackground: setThemeDynBg,
  } = useTheme();

  const [darkMode, setDarkMode] = useState(false);
  const [dynamicBg, setDynamicBg] = useState(true);
  const [notificationSound, setNotificationSound] = useState(true);
  const [colorHue, setColorHue] = useState(DEFAULT_HUE);
  const [nonverbalColor, setNonverbalColor] = useState('#e4ba00');
  const [fontSize, setFontSize] = useState(18);
  const [fontFamily, setFontFamily] = useState('ubuntu');

  // Derive colors from hue
  const derivedColors = hueToColors(colorHue, darkMode);

  // ── Load settings when overlay opens ──
  useEffect(() => {
    if (!open) return;

    setDarkMode(get('darkMode', false));
    setDynamicBg(get('dynamicBackground', true));
    setNotificationSound(get('notificationSound', true));
    setColorHue(parseInt(get('colorHue', String(DEFAULT_HUE)), 10));
    setNonverbalColor(get('nonverbalColor', '#e4ba00'));
    setFontSize(parseInt(get('bubbleFontSize', '18'), 10));
    setFontFamily(get('bubbleFontFamily', 'ubuntu'));
  }, [open, get]);

  // ── Dark mode toggle ──
  const handleDarkModeChange = useCallback((checked) => {
    setDarkMode(checked);
  }, []);

  // ── Save ──
  const handleSave = useCallback(() => {
    const lightColors = hueToColors(colorHue, false);
    const darkColors = hueToColors(colorHue, true);

    setMany({
      darkMode,
      dynamicBackground: dynamicBg,
      notificationSound,
      colorHue: String(colorHue),
      backgroundColor_light: lightColors.bg,
      colorGradient1_light: lightColors.g1,
      color2_light: lightColors.c2,
      backgroundColor_dark: darkColors.bg,
      colorGradient1_dark: darkColors.g1,
      color2_dark: darkColors.c2,
      nonverbalColor,
      bubbleFontSize: String(fontSize),
      bubbleFontFamily: fontFamily,
    });

    setIsDark(darkMode);
    updateColors({
      backgroundColor_light: lightColors.bg,
      colorGradient1_light: lightColors.g1,
      color2_light: lightColors.c2,
      backgroundColor_dark: darkColors.bg,
      colorGradient1_dark: darkColors.g1,
      color2_dark: darkColors.c2,
      nonverbalColor,
    });
    setThemeFontSize(fontSize);
    setThemeFontFamily(resolveFontFamily(fontFamily));
    setThemeFontKey(fontFamily);
    setThemeDynBg(dynamicBg);

    onClose();
  }, [darkMode, dynamicBg, notificationSound, colorHue, nonverbalColor, fontSize, fontFamily, setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeFontKey, setThemeDynBg, onClose]);

  // ── Close without saving ──
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // ── Reset ──
  const handleReset = useCallback(() => {
    if (!window.confirm('Möchtest du die Interface-Einstellungen auf die Standardwerte zurücksetzen?')) {
      return;
    }

    const lightColors = hueToColors(DEFAULT_HUE, false);
    const darkColors = hueToColors(DEFAULT_HUE, true);

    setMany({
      darkMode: false,
      dynamicBackground: true,
      notificationSound: true,
      colorHue: String(DEFAULT_HUE),
      backgroundColor_light: lightColors.bg,
      colorGradient1_light: lightColors.g1,
      color2_light: lightColors.c2,
      backgroundColor_dark: darkColors.bg,
      colorGradient1_dark: darkColors.g1,
      color2_dark: darkColors.c2,
      nonverbalColor: '#e4ba00',
      bubbleFontSize: '18',
      bubbleFontFamily: 'ubuntu',
    });

    setIsDark(false);
    updateColors({
      backgroundColor_light: lightColors.bg,
      colorGradient1_light: lightColors.g1,
      color2_light: lightColors.c2,
      backgroundColor_dark: darkColors.bg,
      colorGradient1_dark: darkColors.g1,
      color2_dark: darkColors.c2,
      nonverbalColor: '#e4ba00',
    });
    setThemeFontSize(18);
    setThemeFontFamily(resolveFontFamily('ubuntu'));
    setThemeFontKey('ubuntu');
    setThemeDynBg(true);

    setDarkMode(false);
    setDynamicBg(true);
    setNotificationSound(true);
    setColorHue(DEFAULT_HUE);
    setNonverbalColor('#e4ba00');
    setFontSize(18);
    setFontFamily('ubuntu');
  }, [setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeFontKey, setThemeDynBg]);

  return (
    <Overlay open={open} onClose={handleClose} width="540px">
      <OverlayHeader title="Interface-Einstellungen" onClose={handleClose} />
      <OverlayBody>

        {/* ═══ Sticky Live Preview ═══ */}
        <div className={styles.ifacePreviewSticky}>
          <InterfacePreview
            isDark={darkMode}
            nonverbalColor={nonverbalColor}
            bgColor={derivedColors.bg}
            gradient1={derivedColors.g1}
            gradient2={derivedColors.c2}
            dynamicBg={dynamicBg}
            fontSize={adjustedFontSize(fontSize, fontFamily)}
            fontFamily={fontFamily}
          />
        </div>

        {/* ═══ Section: Darstellung ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            Darstellung
          </h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>Design-Modus</span>
                <span className={styles.ifaceToggleHint}>
                  {darkMode ? 'Dunkles Farbschema' : 'Helles Farbschema'}
                </span>
              </div>
              <Toggle
                checked={darkMode}
                onChange={handleDarkModeChange}
                id="dark-mode"
              />
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>Dynamischer Hintergrund</span>
                <span className={styles.ifaceToggleHint}>Animierte Farbverläufe im Chat</span>
              </div>
              <Toggle
                checked={dynamicBg}
                onChange={setDynamicBg}
                id="dynamic-bg"
              />
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>Benachrichtigungston</span>
                <span className={styles.ifaceToggleHint}>Sound bei neuen Nachrichten</span>
              </div>
              <Toggle
                checked={notificationSound}
                onChange={setNotificationSound}
                id="notification-sound"
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Farben ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            Farben
          </h3>
          <div className={styles.ifaceCard}>
            {/* Hue Slider */}
            <div className={styles.ifaceFieldGroup}>
              <div className={styles.hueLabelRow}>
                <span className={styles.ifaceFieldLabel}>Farbschema</span>
                <span className={styles.hueValue}>{colorHue}°</span>
              </div>
              <input
                type="range"
                className={styles.hueSlider}
                min={0}
                max={360}
                step={1}
                value={colorHue}
                onChange={(e) => setColorHue(parseInt(e.target.value, 10))}
              />
              <div className={styles.huePreview}>
                <div className={styles.hueSwatchLabeled}>
                  <span className={styles.hueSwatch} style={{ background: derivedColors.bg }} />
                  <span className={styles.hueSwatchLabel}>Basis</span>
                </div>
                <div className={styles.hueSwatchLabeled}>
                  <span className={styles.hueSwatch} style={{ background: derivedColors.g1 }} />
                  <span className={styles.hueSwatchLabel}>Verlauf 1</span>
                </div>
                <div className={styles.hueSwatchLabeled}>
                  <span className={styles.hueSwatch} style={{ background: derivedColors.c2 }} />
                  <span className={styles.hueSwatchLabel}>Verlauf 2</span>
                </div>
              </div>
            </div>

            <div className={styles.ifaceDivider} />

            {/* Nonverbal Color Presets */}
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Nonverbale Text-Farbe</span>
              <span className={styles.ifaceFieldHint}>Für Text zwischen *Sternchen* – z.B. Aktionen, Emotionen</span>
              <div className={styles.colorPresets}>
                {NONVERBAL_PRESETS.map((preset) => (
                  <button
                    key={preset.value}
                    className={`${styles.colorSwatch} ${nonverbalColor === preset.value ? styles.colorSwatchActive : ''}`}
                    style={{ background: preset.value }}
                    onClick={() => setNonverbalColor(preset.value)}
                    title={preset.label}
                    type="button"
                  >
                    {nonverbalColor === preset.value && <span className={styles.swatchCheck}>✓</span>}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ═══ Section: Schrift ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            Schrift
          </h3>
          <div className={styles.ifaceCard}>
            {/* Font Size */}
            <Slider
              label="Schriftgröße"
              value={fontSize}
              onChange={(v) => setFontSize(Math.round(v))}
              min={14}
              max={28}
              step={1}
              displayValue={`${fontSize}px`}
            />

            <div className={styles.ifaceDivider} />

            {/* Font Family Cards */}
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Schriftart</span>
              <div className={styles.fontCardGrid}>
                {FONT_OPTIONS.map((f) => (
                  <button
                    key={f.value}
                    type="button"
                    className={`${styles.fontCard} ${fontFamily === f.value ? styles.fontCardActive : ''}`}
                    onClick={() => setFontFamily(f.value)}
                  >
                    <span
                      className={styles.fontCardPreview}
                      style={{ fontFamily: resolveFontFamily(f.value) }}
                    >
                      {f.icon}
                    </span>
                    <span className={styles.fontCardName}>{f.label}</span>
                    <span className={styles.fontCardDesc}>{f.desc}</span>
                  </button>
                ))}
              </div>
            </div>
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
