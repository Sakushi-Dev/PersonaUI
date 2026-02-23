import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { lazy, Suspense, useState, useEffect } from 'react';
import { AppProvider } from './context/AppProvider';
import { getOnboardingStatus } from './services/onboardingApi';
import { DisclaimerOverlay } from './features/overlays';
import Spinner from './components/Spinner/Spinner';

const ChatPage = lazy(() => import('./features/chat/ChatPage'));
const OnboardingPage = lazy(() => import('./features/onboarding/OnboardingPage'));
const WaitingPage = lazy(() => import('./features/waiting/WaitingPage'));

function App() {
  const location = useLocation();

  // Waiting page rendered early — no onboarding check, no heavy context loading
  if (location.pathname === '/access/waiting') {
    return (
      <Suspense fallback={<Spinner fullScreen />}>
        <WaitingPage />
      </Suspense>
    );
  }

  return (
    <AppProvider>
      <AppRoutes />
    </AppProvider>
  );
}

function AppRoutes() {
  const [onboardingDone, setOnboardingDone] = useState(null); // null = loading
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(true);

  useEffect(() => {
    getOnboardingStatus()
      .then((data) => {
        setOnboardingDone(data.completed ?? true);
        setDisclaimerAccepted(data.disclaimer_accepted ?? true);
      })
      .catch(() => {
        setOnboardingDone(true);
        setDisclaimerAccepted(true);
      });
  }, []);

  if (onboardingDone === null) {
    return <Spinner fullScreen />;
  }

  return (
    <Suspense fallback={<Spinner fullScreen />}>
      <Routes>
        <Route
          path="/"
          element={
            onboardingDone
              ? <>
                  <ChatPage />
                  <DisclaimerOverlay
                    open={!disclaimerAccepted}
                    onAccept={() => setDisclaimerAccepted(true)}
                  />
                </>
              : <Navigate to="/onboarding" replace />
          }
        />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
