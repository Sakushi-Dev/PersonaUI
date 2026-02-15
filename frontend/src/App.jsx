import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense, useState, useEffect } from 'react';
import { getOnboardingStatus } from './services/onboardingApi';
import Spinner from './components/Spinner/Spinner';

const ChatPage = lazy(() => import('./features/chat/ChatPage'));
const OnboardingPage = lazy(() => import('./features/onboarding/OnboardingPage'));
const WaitingPage = lazy(() => import('./features/waiting/WaitingPage'));

function App() {
  const [onboardingDone, setOnboardingDone] = useState(null); // null = loading

  useEffect(() => {
    getOnboardingStatus()
      .then((data) => setOnboardingDone(data.completed ?? true))
      .catch(() => setOnboardingDone(true)); // assume done on error
  }, []);

  if (onboardingDone === null) {
    return <Spinner fullScreen />;
  }

  return (
    <Suspense fallback={<Spinner fullScreen />}>
      <Routes>
        <Route
          path="/"
          element={onboardingDone ? <ChatPage /> : <Navigate to="/onboarding" replace />}
        />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/access/waiting" element={<WaitingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
