// ── ChatPage ──
// Main chat page composing all chat components

import { useEffect, useCallback, useContext, useState, useRef } from 'react';
import { useSession } from '../../hooks/useSession';
import { useSettings } from '../../hooks/useSettings';
import { useTheme } from '../../hooks/useTheme';
import { useOverlay } from '../../hooks/useOverlay';
import { UserContext } from '../../context/UserContext';
import { useMessages } from './hooks/useMessages';
import { useAfterthought } from './hooks/useAfterthought';
import { useSidebar } from './hooks/useSidebar';
import { useSwipe } from './hooks/useSwipe';

import DynamicBackground from '../../components/DynamicBackground/DynamicBackground';
import StaticBackground from '../../components/StaticBackground/StaticBackground';
import Header from './components/Header/Header';
import Sidebar from './components/Sidebar/Sidebar';
import MessageList from './components/MessageList/MessageList';
import ChatInput from './components/ChatInput/ChatInput';
import Spinner from '../../components/Spinner/Spinner';
import ErrorBoundary from '../../components/ErrorBoundary/ErrorBoundary';
import { resolveFontFamily } from '../../utils/constants';

import {
  PersonaSettingsOverlay,
  InterfaceSettingsOverlay,
  ApiKeyOverlay,
  ApiSettingsOverlay,
  ServerSettingsOverlay,
  AvatarEditorOverlay,
  MemoryOverlay,
  CustomSpecsOverlay,
  UserProfileOverlay,
  QRCodeOverlay,
  AccessControlOverlay,
  DebugOverlay,
  CreditExhaustedOverlay,
  ApiWarningOverlay,
} from '../overlays';

import styles from './ChatPage.module.css';

// Wrapper that shows a loading spinner until session + settings are ready
export default function ChatPage() {
  const { loading } = useSession();
  const { loaded: settingsLoaded } = useSettings();

  console.log('[ChatPage] loading:', loading, 'settingsLoaded:', settingsLoaded);

  if (loading || !settingsLoaded) {
    return (
      <div className={styles.page}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
          <Spinner />
          <p style={{ color: '#333', marginTop: '16px', position: 'absolute', top: '55%' }}>
            Lade...
          </p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ChatPageContent />
    </ErrorBoundary>
  );
}

function ChatPageContent() {
  const { sessionId, personaId, character, switchPersona, switchSession, createSession } = useSession();
  const { get } = useSettings();
  const { setIsDark, updateColors, setFontSize: setThemeFontSize, setFontFamily: setThemeFontFamily, setDynamicBackground: setThemeDynBg } = useTheme();

  // ── Sync server settings → theme on initial load ──
  useEffect(() => {
    const dm = get('darkMode', false);
    setIsDark(dm);

    updateColors({
      backgroundColor_light: get('backgroundColor_light', '#a3baff'),
      colorGradient1_light: get('colorGradient1_light', '#66cfff'),
      color2_light: get('color2_light', '#fd91ee'),
      backgroundColor_dark: get('backgroundColor_dark', '#1a2332'),
      colorGradient1_dark: get('colorGradient1_dark', '#2a3f5f'),
      color2_dark: get('color2_dark', '#3d4f66'),
      nonverbalColor: get('nonverbalColor', '#e4ba00'),
    });

    setThemeFontSize(parseInt(get('bubbleFontSize', '18'), 10));
    setThemeFontFamily(resolveFontFamily(get('bubbleFontFamily', 'ubuntu')));
    setThemeDynBg(get('dynamicBackground', true));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once on mount — settings are already loaded at this point

  // ── Core hooks ──
  const {
    isLoading,
    isStreaming,
    streamingStats,
    error,
    hasMore,
    sendMessage,
    cancelStream,
    loadMore,
    deleteLastMsg,
    editLastMsg,
    regenerateLastMsg,
    resendLastMsg,
  } = useMessages();

  const {
    isThinking: afterthoughtThinking,
    startTimer: startAfterthought,
    stopTimer: stopAfterthought,
  } = useAfterthought();

  const sidebar = useSidebar();

  // ── Swipe to open/close sidebar ──
  const swipeHandlers = useSwipe({
    onSwipeRight: sidebar.open,
    onSwipeLeft: sidebar.close,
  });

  // ── Avatar editor target tracking ──
  const [avatarTarget, setAvatarTarget] = useState('persona');
  const [avatarRefreshKey, setAvatarRefreshKey] = useState(0);
  const { setAvatar: setUserAvatar } = useContext(UserContext);
  const personaAvatarCallbackRef = useRef(null);

  // ── Overlay hooks (must be before callbacks that reference them) ──
  const personaSettings = useOverlay();
  const interfaceSettings = useOverlay();
  const apiKey = useOverlay();
  const apiSettings = useOverlay();
  const serverSettings = useOverlay();
  const avatarEditor = useOverlay();
  const memory = useOverlay();
  const customSpecs = useOverlay();
  const userProfile = useOverlay();
  const qrCode = useOverlay();
  const accessControl = useOverlay();
  const debug = useOverlay();
  const creditExhausted = useOverlay();
  const apiWarning = useOverlay();

  // ── Auto-open error overlays on chat errors ──
  useEffect(() => {
    if (!error) return;
    if (error.type === 'credit_balance_exhausted') {
      creditExhausted.open();
    } else if (error.type === 'api_key_missing') {
      apiWarning.open();
    }
  }, [error]);

  const handleOpenAvatarEditor = useCallback((target = 'persona') => {
    setAvatarTarget(target);
    avatarEditor.open();
  }, [avatarEditor]);

  // ── Avatar saved callback — update UserContext + trigger profile refresh ──
  const handleAvatarSaved = useCallback((filename, type) => {
    if (avatarTarget === 'user') {
      setUserAvatar(filename, type);
      setAvatarRefreshKey((k) => k + 1);
    } else if (avatarTarget === 'persona') {
      // Route avatar data back to PersonaSettingsOverlay
      personaAvatarCallbackRef.current?.(filename, type);
    }
  }, [avatarTarget, setUserAvatar]);

  // ── Start afterthought timer after user sends message ──
  const handleSend = useCallback((text) => {
    sendMessage(text);
    startAfterthought(true);
  }, [sendMessage, startAfterthought]);

  // ── New chat ──
  const handleNewChat = useCallback(async () => {
    try {
      await createSession(personaId);
      sidebar.close();
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  }, [personaId, createSession, sidebar]);

  // ── Sidebar persona actions ──
  // Matches legacy openPersonaLatestSession: switch to persona's latest session
  // AND show sessions view simultaneously
  const handleSelectPersona = useCallback(async (pid) => {
    sidebar.showSessions(pid);
    try {
      await switchPersona(pid);
    } catch (err) {
      console.warn('Failed to open persona session:', err);
    }
  }, [sidebar, switchPersona]);

  // ── Dynamic background ──
  const dynamicBg = get('dynamicBackground', true);

  return (
    <div className={styles.page} {...swipeHandlers}>
      {dynamicBg ? <DynamicBackground /> : <StaticBackground />}

      <Header
        onToggleSidebar={sidebar.toggle}
        onOpenPersonaSettings={personaSettings.open}
        onOpenInterfaceSettings={interfaceSettings.open}
        onOpenApiKey={apiKey.open}
        onOpenApiSettings={apiSettings.open}
        onOpenServerSettings={serverSettings.open}
        onOpenMemory={memory.open}
        onOpenUserProfile={userProfile.open}
        onOpenQRCode={qrCode.open}
        onOpenAccessControl={accessControl.open}
      />

      <Sidebar
        isOpen={sidebar.isOpen}
        view={sidebar.view}
        selectedPersonaId={sidebar.selectedPersonaId}
        onClose={sidebar.close}
        onShowPersonas={sidebar.showPersonas}
        onSelectPersona={handleSelectPersona}
        onNewChat={handleNewChat}
      />

      <MessageList
        isStreaming={isStreaming}
        afterthoughtStreaming={afterthoughtThinking}
        hasMore={hasMore}
        onLoadMore={loadMore}
        onNewChat={handleNewChat}
        onDeleteLast={deleteLastMsg}
        onEditLast={editLastMsg}
        onRegenerateLast={regenerateLastMsg}
        onResendLast={resendLastMsg}
      />

      <ChatInput
        onSend={handleSend}
        disabled={isLoading || !sessionId}
        isStreaming={isStreaming}
        onCancel={cancelStream}
        placeholder={!sessionId ? 'Bitte erstelle zuerst einen neuen Chat...' : 'Deine Nachricht...'}
      />

      {/* ── Overlays ── */}
      <PersonaSettingsOverlay
        open={personaSettings.isOpen}
        onClose={personaSettings.close}
        onOpenAvatarEditor={handleOpenAvatarEditor}
        onOpenCustomSpecs={() => { personaSettings.close(); customSpecs.open(); }}
        avatarCallbackRef={personaAvatarCallbackRef}
      />
      <InterfaceSettingsOverlay
        open={interfaceSettings.isOpen}
        onClose={interfaceSettings.close}
      />
      <ApiKeyOverlay
        open={apiKey.isOpen}
        onClose={apiKey.close}
      />
      <ApiSettingsOverlay
        open={apiSettings.isOpen}
        onClose={apiSettings.close}
      />
      <ServerSettingsOverlay
        open={serverSettings.isOpen}
        onClose={serverSettings.close}
      />
      <AvatarEditorOverlay
        open={avatarEditor.isOpen}
        onClose={avatarEditor.close}
        personaId={personaId}
        target={avatarTarget}
        onSaved={handleAvatarSaved}
        stacked
      />
      <MemoryOverlay
        open={memory.isOpen}
        onClose={memory.close}
      />
      <CustomSpecsOverlay
        open={customSpecs.isOpen}
        onClose={customSpecs.close}
      />
      <UserProfileOverlay
        open={userProfile.isOpen}
        onClose={userProfile.close}
        onOpenAvatarEditor={() => handleOpenAvatarEditor('user')}
        avatarRefreshKey={avatarRefreshKey}
      />
      <QRCodeOverlay
        open={qrCode.isOpen}
        onClose={qrCode.close}
        onOpenServerSettings={() => { qrCode.close(); serverSettings.open(); }}
      />
      <AccessControlOverlay
        open={accessControl.isOpen}
        onClose={accessControl.close}
      />
      <DebugOverlay
        open={debug.isOpen}
        onClose={debug.close}
      />
      <CreditExhaustedOverlay
        open={creditExhausted.isOpen}
        onClose={creditExhausted.close}
      />
      <ApiWarningOverlay
        open={apiWarning.isOpen}
        onClose={apiWarning.close}
        onOpenApiKey={() => { apiWarning.close(); apiKey.open(); }}
      />
    </div>
  );
}
