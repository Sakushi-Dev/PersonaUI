// ── OnboardingPage ──
// 5-step wizard: Welcome → Profile → Interface → API → Finish

import { useState, useCallback } from 'react';
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

  // Collected data across steps
  const [profileData, setProfileData] = useState({
    user_name: '',
    user_avatar: null,
    user_avatar_type: null,
    user_type: '',
    user_gender: '',
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

  const handleNext = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleFinish = useCallback(async () => {
    setSaving(true);
    try {
      // Save profile
      await updateUserProfile(profileData);

      // Save settings
      await updateSettings({
        darkMode: interfaceData.darkMode,
        nonverbalColor: interfaceData.nonverbalColor,
        contextLimit: apiData.contextLimit,
        nachgedankeEnabled: apiData.nachgedankeEnabled,
      });

      // Save API key if provided
      if (apiData.apiKey) {
        await saveApiKey(apiData.apiKey);
      }

      // Mark onboarding complete
      await completeOnboarding();

      // Store dark mode locally
      storage.setItem('darkMode', interfaceData.darkMode);

      // Full page reload to re-initialize all contexts with fresh data
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
      <div className={styles.container}>
        <ProgressBar progress={progress} />
        <StepIndicator current={step} total={TOTAL_STEPS} onGoTo={(s) => s <= step && setStep(s)} />

        <div className={styles.content}>
          {step === 0 && (
            <StepWelcome onNext={handleNext} />
          )}
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
