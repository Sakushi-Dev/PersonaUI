// ── Onboarding API Service ──

import { apiGet, apiPost } from './apiClient';

export function getOnboardingStatus() {
  return apiGet('/api/onboarding/status');
}

export function completeOnboarding(data) {
  return apiPost('/api/onboarding/complete', data);
}
