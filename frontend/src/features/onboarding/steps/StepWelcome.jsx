// ── Step: Welcome ──

import { LANGUAGES } from '../../../utils/languages';
import { t } from '../useTranslation';
import styles from './Steps.module.css';

export default function StepWelcome({ onNext, language, onLanguageChange }) {
  const s = t(language, 'welcome');

  return (
    <div className={styles.card}>
      <div className={styles.welcomeCard}>

        {/* Language Toggle — top right */}
        <div className={styles.langToggle}>
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              className={`${styles.langBtn} ${language === lang.code ? styles.langBtnActive : ''}`}
              onClick={() => onLanguageChange(lang.code)}
              title={lang.name}
            >
              {lang.label}
            </button>
          ))}
        </div>

        <div className={styles.logo}>
          <div className={styles.logoInner}>
            <img src="/persona_ui.ico" alt="PersonaUI" className={styles.logoIcon} />
          </div>
        </div>
        <h1 className={styles.welcomeTitle}>{s.title}</h1>
        <p className={styles.welcomeSubtitle}>{s.subtitle}</p>

        <div className={styles.welcomeFeatures}>
          <div className={styles.feature}>
            <span className={styles.featureTag}>01</span>
            <div className={styles.featureText}>
              <strong>{s.feature1Title}</strong>
              <span className={styles.featureTyped}>{s.feature1Desc}</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>02</span>
            <div className={styles.featureText}>
              <strong>{s.feature2Title}</strong>
              <span className={styles.featureTyped}>{s.feature2Desc}</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>03</span>
            <div className={styles.featureText}>
              <strong>{s.feature3Title}</strong>
              <span className={styles.featureTyped}>{s.feature3Desc}</span>
            </div>
          </div>
          <div className={styles.feature}>
            <span className={styles.featureTag}>04</span>
            <div className={styles.featureText}>
              <strong>{s.feature4Title}</strong>
              <span className={styles.featureTyped}>{s.feature4Desc}</span>
            </div>
          </div>
        </div>

        <p className={styles.welcomeHint}>{s.hint}</p>

        <button className={styles.btnPrimary + ' ' + styles.btnLarge} onClick={onNext}>
          {s.startBtn}
        </button>
      </div>
    </div>
  );
}
