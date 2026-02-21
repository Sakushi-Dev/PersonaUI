// ── OnboardingPage ──
// 8-step wizard: Welcome → Profile → Interface → Context → Cortex → Afterthought → API → Finish

import { useState, useCallback, useEffect } from 'react';
import { useTheme } from '../../hooks/useTheme';
import DynamicBackground from '../../components/DynamicBackground/DynamicBackground';
import StepWelcome from './steps/StepWelcome';
import StepProfile from './steps/StepProfile';
import StepInterface from './steps/StepInterface';
import StepContext from './steps/StepContext';
import StepCortex from './steps/StepCortex';
import StepAfterthought from './steps/StepAfterthought';
import StepApi from './steps/StepApi';
import StepFinish from './steps/StepFinish';
import ProgressBar from './components/ProgressBar';
import StepIndicator from './components/StepIndicator';
import { updateUserProfile } from '../../services/userProfileApi';
import { updateSettings, getSettings } from '../../services/settingsApi';
import { saveApiKey } from '../../services/serverApi';
import { completeOnboarding } from '../../services/onboardingApi';
import * as storage from '../../utils/storage';
import { DEFAULT_LANGUAGE } from '../../utils/languages';
import styles from './OnboardingPage.module.css';

const TOTAL_STEPS = 8;

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const { setIsDark, setDynamicBackground } = useTheme();

  // Ensure dynamic background is visible during onboarding
  useEffect(() => {
    setDynamicBackground(true);
  }, [setDynamicBackground]);

  // Collected data across steps
  const [profileData, setProfileData] = useState({
    user_name: '',
    user_avatar: null,
    user_avatar_type: null,
    user_gender: null,
    user_interested_in: [],
    user_info: '',
  });

  const [interfaceData, setInterfaceData] = useState({
    darkMode: false,
    nonverbalColor: '#e4ba00',
  });

  const [cortexData, setCortexData] = useState({
    cortexEnabled: true,
    cortexFrequency: 'medium',
  });

  const [afterthoughtData, setAfterthoughtData] = useState({
    nachgedankeMode: 'off',
  });

  const [contextData, setContextData] = useState({
    contextLimit: '200',
  });

  const [apiData, setApiData] = useState({
    apiKey: '',
    apiKeyValid: false,
  });

  const [language, setLanguage] = useState(DEFAULT_LANGUAGE);

  // Load saved language from user_settings on mount
  useEffect(() => {
    getSettings()
      .then((data) => { if (data?.language) setLanguage(data.language); })
      .catch(() => {});
  }, []);

  // Save language immediately when changed
  const handleLanguageChange = useCallback((lang) => {
    setLanguage(lang);
    updateSettings({ language: lang }).catch(() => {});
  }, []);

  const goTo = useCallback((s) => {
    if (s >= 0 && s < TOTAL_STEPS) setStep(s);
  }, []);

  const handleNext = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  // Dark mode toggle handler — applies immediately via ThemeContext
  const handleDarkModeChange = useCallback((checked) => {
    setIsDark(checked);
    setInterfaceData((prev) => ({ ...prev, darkMode: checked }));
  }, [setIsDark]);

  const handleFinish = useCallback(async () => {
    setSaving(true);
    try {
      await updateUserProfile(profileData);

      await updateSettings({
        language,
        darkMode: interfaceData.darkMode,
        nonverbalColor: interfaceData.nonverbalColor,
        contextLimit: contextData.contextLimit,
        nachgedankeMode: afterthoughtData.nachgedankeMode,
        cortexEnabled: cortexData.cortexEnabled,
        cortexFrequency: cortexData.cortexFrequency,
      });

      if (apiData.apiKey) {
        await saveApiKey(apiData.apiKey);
      }

      await completeOnboarding();
      storage.setItem('darkMode', interfaceData.darkMode);
      window.location.href = '/';
    } catch (err) {
      console.error('Onboarding finish failed:', err);
    } finally {
      setSaving(false);
    }
  }, [profileData, interfaceData, contextData, cortexData, afterthoughtData, apiData, language]);

  const progress = (step / (TOTAL_STEPS - 1)) * 100;

  return (
    <div className={styles.page}>
      {/* Use existing DynamicBackground component */}
      <DynamicBackground />

      {/* Fixed Progress Bar */}
      <ProgressBar progress={progress} />

      {/* Fixed Step Indicators */}
      <StepIndicator
        current={step}
        total={TOTAL_STEPS}
        onGoTo={(s) => s <= step + 1 && goTo(s)}
      />

      {/* Step Container */}
      <div className={styles.container}>
        <div className={styles.stepWrapper} key={step}>
          {step === 0 && <StepWelcome onNext={handleNext} language={language} onLanguageChange={handleLanguageChange} />}
          {step === 1 && (
            <StepProfile
              data={profileData}
              onChange={setProfileData}
              onNext={handleNext}
              onBack={handleBack}
              language={language}
            />
          )}
          {step === 2 && (
            <StepInterface
              data={interfaceData}
              onChange={setInterfaceData}
              onDarkModeChange={handleDarkModeChange}
              onNext={handleNext}
              onBack={handleBack}
              language={language}
            />
          )}
          {step === 3 && (
            <StepContext
              data={contextData}
              onChange={setContextData}
              onNext={handleNext}
              onBack={handleBack}
              language={language}
            />
          )}
          {step === 4 && (
            <StepCortex
              data={cortexData}
              onChange={setCortexData}
              onNext={handleNext}
              onBack={handleBack}
              language={language}
            />
          )}
          {step === 5 && (
            <StepAfterthought
              data={afterthoughtData}
              onChange={setAfterthoughtData}
              onNext={handleNext}
              onBack={handleBack}
              language={language}
            />
          )}
          {step === 6 && (
            <StepApi
              data={apiData}
              onChange={setApiData}
              onNext={handleNext}
              onBack={handleBack}
              language={language}
            />
          )}
          {step === 7 && (
            <StepFinish
              hasApiKey={apiData.apiKeyValid}
              onFinish={handleFinish}
              saving={saving}
              language={language}
            />
          )}
        </div>
      </div>
    </div>
  );
}
