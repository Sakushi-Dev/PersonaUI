// ── OnboardingPage ──
// 5-step wizard: Welcome → Profile → Interface → API → Finish
// 1:1 match with legacy onboarding

import { useState, useCallback, useEffect } from 'react';
import { useTheme } from '../../hooks/useTheme';
import DynamicBackground from '../../components/DynamicBackground/DynamicBackground';
import StepWelcome from './steps/StepWelcome';
import StepProfile from './steps/StepProfile';
import StepInterface from './steps/StepInterface';
import StepApi from './steps/StepApi';
import StepFinish from './steps/StepFinish';
import ProgressBar from './components/ProgressBar';
import StepIndicator from './components/StepIndicator';
import { updateUserProfile } from '../../services/userProfileApi';
import { updateSettings } from '../../services/settingsApi';
import { saveApiKey } from '../../services/serverApi';
import { completeOnboarding } from '../../services/onboardingApi';
import * as storage from '../../utils/storage';
import styles from './OnboardingPage.module.css';

const TOTAL_STEPS = 5;

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
    user_type: null,
    user_type_description: null,
    user_gender: null,
    user_interested_in: [],
    user_info: '',
  });

  const [interfaceData, setInterfaceData] = useState({
    darkMode: false,
    nonverbalColor: '#e4ba00',
  });

  const [apiData, setApiData] = useState({
    contextLimit: '25',
    nachgedankeEnabled: false,
    apiKey: '',
    apiKeyValid: false,
  });

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
        darkMode: interfaceData.darkMode,
        nonverbalColor: interfaceData.nonverbalColor,
        contextLimit: apiData.contextLimit,
        nachgedankeEnabled: apiData.nachgedankeEnabled,
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
  }, [profileData, interfaceData, apiData]);

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
          {step === 0 && <StepWelcome onNext={handleNext} />}
          {step === 1 && (
            <StepProfile
              data={profileData}
              onChange={setProfileData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 2 && (
            <StepInterface
              data={interfaceData}
              onChange={setInterfaceData}
              onDarkModeChange={handleDarkModeChange}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 3 && (
            <StepApi
              data={apiData}
              onChange={setApiData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 4 && (
            <StepFinish
              hasApiKey={apiData.apiKeyValid}
              onFinish={handleFinish}
              saving={saving}
            />
          )}
        </div>
      </div>
    </div>
  );
}
