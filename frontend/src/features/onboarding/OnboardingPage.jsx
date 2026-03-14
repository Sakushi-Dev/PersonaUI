// ── OnboardingPage ──
// 8-step wizard: Welcome → Profile → Interface → Context → Cortex → Afterthought → API → Finish

import { useState, useCallback, useEffect } from 'react';
import { useTheme } from '../../hooks/useTheme';
import { useLanguage } from '../../hooks/useLanguage';
import { useSettings } from '../../hooks/useSettings';
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
import { getUserProfile, updateUserProfile } from '../../services/userProfileApi';
import { getSettings, updateSettings } from '../../services/settingsApi';
import { saveApiKey, checkApiStatus } from '../../services/serverApi';
import { getCortexSettings, saveCortexSettings } from '../../services/cortexApi';
import { completeOnboarding } from '../../services/onboardingApi';
import * as storage from '../../utils/storage';
import styles from './OnboardingPage.module.css';

const TOTAL_STEPS = 8;

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const { setIsDark, setDynamicBackground } = useTheme();
  const { language } = useLanguage();
  const { set } = useSettings();

  // Detect mobile for background suppression
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 480);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= 480);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  // Ensure dynamic background is visible during onboarding
  useEffect(() => {
    setDynamicBackground(true);
  }, [setDynamicBackground]);

  // Collected data across steps
  const [profileData, setProfileData] = useState({
    userName: '',
    userAvatar: null,
    userAvatarType: null,
    userGender: null,
    userInterestedIn: [],
    userInfo: '',
    personaLanguage: 'english',
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
    afterthoughtMode: 'off',
  });

  const [contextData, setContextData] = useState({
    contextLimit: '100',
  });

  const [apiData, setApiData] = useState({
    apiKey: '',
    apiKeyValid: false,
  });

  // Pre-fill with existing data when re-running onboarding
  useEffect(() => {
    Promise.allSettled([
      getUserProfile(),
      getSettings(),
      getCortexSettings(),
    ]).then(([profileRes, settingsRes, cortexRes]) => {
      if (profileRes.status === 'fulfilled') {
        const p = profileRes.value?.profile;
        if (p) {
          setProfileData((prev) => ({
            ...prev,
            userName: p.userName || prev.userName,
            userAvatar: p.userAvatar ?? prev.userAvatar,
            userAvatarType: p.userAvatarType ?? prev.userAvatarType,
            userGender: p.userGender ?? prev.userGender,
            userInterestedIn: Array.isArray(p.userInterestedIn) && p.userInterestedIn.length
              ? p.userInterestedIn : prev.userInterestedIn,
            userInfo: p.userInfo || prev.userInfo,
            personaLanguage: p.personaLanguage || prev.personaLanguage,
          }));
        }
      }
      if (settingsRes.status === 'fulfilled') {
        const s = settingsRes.value?.settings;
        if (s?.apiKey) {
          setApiData({ apiKey: s.apiKey, apiKeyValid: false });
          checkApiStatus().then((r) => {
            if (r?.has_api_key) setApiData({ apiKey: s.apiKey, apiKeyValid: true });
          }).catch(() => {});
        }
        if (s) {
          setInterfaceData((prev) => ({
            darkMode: s.darkMode ?? prev.darkMode,
            nonverbalColor: s.nonverbalColor || prev.nonverbalColor,
          }));
          setContextData((prev) => ({
            contextLimit: s.contextLimit != null ? String(s.contextLimit) : prev.contextLimit,
          }));
          setAfterthoughtData((prev) => ({
            afterthoughtMode: s.afterthoughtMode || prev.afterthoughtMode,
          }));
        }
      }
      if (cortexRes.status === 'fulfilled') {
        const c = cortexRes.value?.settings;
        if (c) {
          setCortexData((prev) => ({
            cortexEnabled: c.enabled ?? prev.cortexEnabled,
            cortexFrequency: c.frequency || prev.cortexFrequency,
          }));
        }
      }
    });
  }, []);

  // Save language immediately when changed (via SettingsContext)
  const handleLanguageChange = useCallback((lang) => {
    set('uiLanguage', lang);
  }, [set]);

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
    console.log('[Onboarding] handleFinish profileData:', JSON.stringify(profileData));
    try {
      await updateUserProfile(profileData);

      await updateSettings({
        uiLanguage: language,
        darkMode: interfaceData.darkMode,
        nonverbalColor: interfaceData.nonverbalColor,
        contextLimit: contextData.contextLimit,
        afterthoughtMode: afterthoughtData.afterthoughtMode,
      });

      await saveCortexSettings({
        enabled: cortexData.cortexEnabled,
        frequency: cortexData.cortexFrequency,
      }).catch((err) => console.warn('Failed to sync cortex settings:', err));

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
      {/* Hide background on mobile — card is the only frame */}
      {!isMobile && <DynamicBackground />}

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
          {step === 0 && <StepWelcome onNext={handleNext} onLanguageChange={handleLanguageChange} />}
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
            <StepContext
              data={contextData}
              onChange={setContextData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 4 && (
            <StepCortex
              data={cortexData}
              onChange={setCortexData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 5 && (
            <StepAfterthought
              data={afterthoughtData}
              onChange={setAfterthoughtData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 6 && (
            <StepApi
              data={apiData}
              onChange={setApiData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}
          {step === 7 && (
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
