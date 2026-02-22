// ── InterfaceSettingsOverlay ──
// Structured into: Preview → Appearance → Colors → Font

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSettings } from '../../hooks/useSettings';
import { useTheme } from '../../hooks/useTheme';
import { useLanguage } from '../../hooks/useLanguage';
import { resolveFontFamily, adjustedFontSize, hueToColors, DEFAULT_HUE, NONVERBAL_PRESETS } from '../../utils/constants';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { MonitorIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Slider from '../../components/Slider/Slider';
import Button from '../../components/Button/Button';
import InterfacePreview from '../../components/InterfacePreview/InterfacePreview';
import styles from './Overlays.module.css';

// Font option keys – desc is resolved via i18n
const FONT_OPTION_KEYS = [
  { value: 'ubuntu',  label: 'Ubuntu',          descKey: 'fontDefault',   icon: 'Aa' },
  { value: 'comic',   label: 'Comic Sans',      descKey: 'fontPlayful',   icon: 'Aa' },
  { value: 'times',   label: 'Times New Roman',  descKey: 'fontClassic',   icon: 'Aa' },
  { value: 'courier', label: 'Courier New',      descKey: 'fontMonospace', icon: 'Aa' },
  { value: 'pixel',   label: 'Pixel',            descKey: 'fontRetro',     icon: 'Px' },
  { value: 'console', label: 'Console',          descKey: 'fontTerminal',  icon: '>' },
];

export default function InterfaceSettingsOverlay({ open, onClose, panelOnly }) {
  const { get, setMany } = useSettings();
  const { t } = useLanguage();
  const s = t('interfaceSettings');
  const sc = t('common');
  const {
    setIsDark,
    updateColors,
    setFontSize: setThemeFontSize,
    setFontFamily: setThemeFontFamily,
    setFontKey: setThemeFontKey,
    setDynamicBackground: setThemeDynBg,
  } = useTheme();

  const [language, setLanguage] = useState('en');
  const [darkMode, setDarkMode] = useState(false);
  const [dynamicBg, setDynamicBg] = useState(true);
  const [notificationSound, setNotificationSound] = useState(true);
  const [colorHue, setColorHue] = useState(DEFAULT_HUE);
  const [nonverbalColor, setNonverbalColor] = useState('#e4ba00');
  const [fontSize, setFontSize] = useState(18);
  const [fontFamily, setFontFamily] = useState('ubuntu');

  // Resolve font option descriptions via i18n
  const fontOptions = useMemo(() =>
    FONT_OPTION_KEYS.map(f => ({ ...f, desc: s[f.descKey] || f.descKey })),
    [s]
  );

  // Derive colors from hue
  const derivedColors = hueToColors(colorHue, darkMode);

  // ── Load settings when overlay opens ──
  useEffect(() => {
    if (!open) return;

    setLanguage(get('language', 'en'));
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
      language,
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
  }, [language, darkMode, dynamicBg, notificationSound, colorHue, nonverbalColor, fontSize, fontFamily, setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeFontKey, setThemeDynBg, onClose]);

  // ── Close without saving ──
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // ── Reset ──
  const handleReset = useCallback(() => {
    if (!window.confirm(s.confirmReset)) {
      return;
    }

    const lightColors = hueToColors(DEFAULT_HUE, false);
    const darkColors = hueToColors(DEFAULT_HUE, true);

    setMany({
      language: 'en',
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

    setLanguage('en');
    setDarkMode(false);
    setDynamicBg(true);
    setNotificationSound(true);
    setColorHue(DEFAULT_HUE);
    setNonverbalColor('#e4ba00');
    setFontSize(18);
    setFontFamily('ubuntu');
  }, [setMany, setIsDark, updateColors, setThemeFontSize, setThemeFontFamily, setThemeFontKey, setThemeDynBg]);

  return (
    <Overlay open={open} onClose={handleClose} width="540px" panelOnly={panelOnly}>
      <OverlayHeader title={s.title} icon={<MonitorIcon size={20} />} onClose={handleClose} />
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

        {/* ═══ Section: Appearance ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            {s.appearance}
          </h3>
          <div className={styles.ifaceCard}>

            {/* Language Selector */}
            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>{s.language}</span>
                <span className={styles.ifaceToggleHint}>
                  {language === 'de' ? 'Deutsch' : 'English'}
                </span>
              </div>
              <div className={styles.langSelector}>
                <button
                  type="button"
                  className={`${styles.langOption} ${language === 'de' ? styles.langOptionActive : ''}`}
                  onClick={() => setLanguage('de')}
                >
                  DE
                </button>
                <button
                  type="button"
                  className={`${styles.langOption} ${language === 'en' ? styles.langOptionActive : ''}`}
                  onClick={() => setLanguage('en')}
                >
                  EN
                </button>
              </div>
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceToggleRow}>
              <div className={styles.ifaceToggleInfo}>
                <span className={styles.ifaceToggleLabel}>{s.designMode}</span>
                <span className={styles.ifaceToggleHint}>
                  {darkMode ? s.darkScheme : s.lightScheme}
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
                <span className={styles.ifaceToggleLabel}>{s.dynamicBg}</span>
                <span className={styles.ifaceToggleHint}>{s.dynamicBgHint}</span>
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
                <span className={styles.ifaceToggleLabel}>{s.notificationSound}</span>
                <span className={styles.ifaceToggleHint}>{s.notificationSoundHint}</span>
              </div>
              <Toggle
                checked={notificationSound}
                onChange={setNotificationSound}
                id="notification-sound"
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Colors ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            {s.colors}
          </h3>
          <div className={styles.ifaceCard}>
            {/* Hue Slider */}
            <div className={styles.ifaceFieldGroup}>
              <div className={styles.hueLabelRow}>
                <span className={styles.ifaceFieldLabel}>{s.colorScheme}</span>
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
                  <span className={styles.hueSwatchLabel}>{s.base}</span>
                </div>
                <div className={styles.hueSwatchLabeled}>
                  <span className={styles.hueSwatch} style={{ background: derivedColors.g1 }} />
                  <span className={styles.hueSwatchLabel}>{s.gradient1}</span>
                </div>
                <div className={styles.hueSwatchLabeled}>
                  <span className={styles.hueSwatch} style={{ background: derivedColors.c2 }} />
                  <span className={styles.hueSwatchLabel}>{s.gradient2}</span>
                </div>
              </div>
            </div>

            <div className={styles.ifaceDivider} />

            {/* Nonverbal Color Presets */}
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>{s.nonverbalColor}</span>
              <span className={styles.ifaceFieldHint}>{s.nonverbalHint}</span>
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

        {/* ═══ Section: Font ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            {s.font}
          </h3>
          <div className={styles.ifaceCard}>
            {/* Font Size */}
            <Slider
              label={s.fontSize}
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
              <span className={styles.ifaceFieldLabel}>{s.fontFamily}</span>
              <div className={styles.fontCardGrid}>
                {fontOptions.map((f) => (
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
        <Button variant="secondary" onClick={handleReset}>{sc.reset}</Button>
        <Button variant="primary" onClick={handleSave}>{sc.save}</Button>
      </OverlayFooter>
    </Overlay>
  );
}
