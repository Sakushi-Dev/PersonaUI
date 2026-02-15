// ── Combined App Provider ──

import { ThemeProvider } from './ThemeContext';
import { SettingsProvider } from './SettingsContext';
import { SessionProvider } from './SessionContext';
import { UserProvider } from './UserContext';
import ToastContainer from '../components/Toast/ToastContainer';

export function AppProvider({ children }) {
  return (
    <ThemeProvider>
      <SettingsProvider>
        <SessionProvider>
          <UserProvider>
            <ToastContainer>
              {children}
            </ToastContainer>
          </UserProvider>
        </SessionProvider>
      </SettingsProvider>
    </ThemeProvider>
  );
}
