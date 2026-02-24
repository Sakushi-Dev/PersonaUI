// ── ChatPage ──
// Main chat page composing all chat components

import { useEffect, useCallback, useContext, useState, useRef, useMemo } from 'react';
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
import ContextBar from './components/ChatInput/ContextBar';
import CortexUpdateIndicator from './components/CortexUpdateIndicator/CortexUpdateIndicator';
import Spinner from '../../components/Spinner/Spinner';
import ErrorBoundary from '../../components/ErrorBoundary/ErrorBoundary';
import AccessNotification from './components/AccessNotification/AccessNotification';
import { resolveFontFamily } from '../../utils/constants';
import { useLanguage } from '../../hooks/useLanguage';

import {
  PersonaSettingsOverlay,
  InterfaceSettingsOverlay,
  ApiKeyOverlay,
  ApiSettingsOverlay,
  ServerSettingsOverlay,
  AvatarEditorOverlay,
  CortexOverlay,
  CustomSpecsOverlay,
  CustomSpecsListOverlay,
  UserProfileOverlay,
  QRCodeOverlay,
  AccessControlOverlay,
  DebugOverlay,
  CreditExhaustedOverlay,
  ApiWarningOverlay,
  SupportOverlay,
  PatchNotesOverlay,
} from '../overlays';

import styles from './ChatPage.module.css';

// Wrapper that shows a loading spinner until session + settings are ready
export default function ChatPage({ disclaimerAccepted = true }) {
  const { loading } = useSession();
  const { loaded: settingsLoaded } = useSettings();
  const { t } = useLanguage();
  const s = t('chat');

  console.log('[ChatPage] loading:', loading, 'settingsLoaded:', settingsLoaded);

  if (loading || !settingsLoaded) {
    return (
      <div className={styles.page}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Spinner />
          <p style={{ color: '#333', marginTop: '16px', position: 'absolute', top: '55%' }}>
            {s.loadingText}
          </p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ChatPageContent disclaimerAccepted={disclaimerAccepted} />
    </ErrorBoundary>
  );
}

function ChatPageContent({ disclaimerAccepted = true }) {
  const { sessionId, personaId, character, switchPersona, switchSession, createSession, pendingAutoFirstMessage, setPendingAutoFirstMessage } = useSession();
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
    triggerAutoFirstMessage,
  } = useMessages();

  // ── Auto First Message: consume pending signal from SessionContext ──
  // Wait until disclaimer is accepted before triggering (post-onboarding flow)
  useEffect(() => {
    if (pendingAutoFirstMessage && sessionId && !isLoading && !isStreaming && disclaimerAccepted) {
      setPendingAutoFirstMessage(false);
      triggerAutoFirstMessage(sessionId, personaId);
    }
  }, [pendingAutoFirstMessage, sessionId, isLoading, isStreaming, personaId, triggerAutoFirstMessage, setPendingAutoFirstMessage, disclaimerAccepted]);

  const {
    isThinking: afterthoughtThinking,
    onUserMessage: onAfterthoughtMessage,
    stopTimer: stopAfterthought,
    pauseTimer: pauseAfterthought,
    resumeTimer: resumeAfterthought,
    consumePendingThought,
  } = useAfterthought();

  // ── Pause afterthought while AI is streaming, resume when done ──
  useEffect(() => {
    if (isStreaming) {
      pauseAfterthought();
    } else {
      resumeAfterthought();
    }
  }, [isStreaming, pauseAfterthought, resumeAfterthought]);

  const sidebar = useSidebar();

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
  const cortex = useOverlay();
  const customSpecs = useOverlay();
  const customSpecsList = useOverlay();
  const userProfile = useOverlay();
  const qrCode = useOverlay();
  const accessControl = useOverlay();
  const debug = useOverlay();
  const creditExhausted = useOverlay();
  const apiWarning = useOverlay();
  const support = useOverlay();
  const patchNotes = useOverlay();

  // ── Close all overlays (used to ensure only one is open at a time) ──
  const closeAllOverlays = useCallback(() => {
    personaSettings.close();
    interfaceSettings.close();
    apiKey.close();
    apiSettings.close();
    serverSettings.close();
    avatarEditor.close();
    cortex.close();
    customSpecs.close();
    customSpecsList.close();
    userProfile.close();
    qrCode.close();
    accessControl.close();
    debug.close();
    creditExhausted.close();
    apiWarning.close();
    support.close();
    patchNotes.close();
  }, [personaSettings, interfaceSettings, apiKey, apiSettings, serverSettings, avatarEditor, cortex, customSpecs, customSpecsList, userProfile, qrCode, accessControl, debug, creditExhausted, apiWarning, support, patchNotes]);

  // ── Exclusive open helpers (close others first) ──
  const openExclusive = useCallback((overlay) => {
    closeAllOverlays();
    overlay.open();
  }, [closeAllOverlays]);

  // ── Swipeable overlay sequence (mobile navigation) ──
  const overlaySequence = useMemo(() => [
    { id: 'userProfile',        hook: userProfile },
    { id: 'apiKey',             hook: apiKey },
    { id: 'cortex',             hook: cortex },
    { id: 'personaSettings',    hook: personaSettings },
    { id: 'interfaceSettings',  hook: interfaceSettings },
    { id: 'apiSettings',        hook: apiSettings },
    { id: 'support',            hook: support },
    { id: 'patchNotes',         hook: patchNotes },
  ], [userProfile, apiKey, cortex, personaSettings, interfaceSettings, apiSettings, support, patchNotes]);

  const activeOverlayId = useMemo(() => {
    for (const item of overlaySequence) {
      if (item.hook.isOpen) return item.id;
    }
    return null;
  }, [overlaySequence]);

  // ── Compute anyOverlayOpen ──
  const anyOverlayOpen = useMemo(() => {
    return personaSettings.isOpen || interfaceSettings.isOpen || apiKey.isOpen ||
      apiSettings.isOpen || serverSettings.isOpen || avatarEditor.isOpen ||
      cortex.isOpen || customSpecs.isOpen || customSpecsList.isOpen ||
      userProfile.isOpen || qrCode.isOpen || accessControl.isOpen ||
      debug.isOpen || creditExhausted.isOpen || apiWarning.isOpen ||
      support.isOpen || patchNotes.isOpen;
  }, [personaSettings.isOpen, interfaceSettings.isOpen, apiKey.isOpen, apiSettings.isOpen, serverSettings.isOpen, avatarEditor.isOpen, cortex.isOpen, customSpecs.isOpen, customSpecsList.isOpen, userProfile.isOpen, qrCode.isOpen, accessControl.isOpen, debug.isOpen, creditExhausted.isOpen, apiWarning.isOpen, support.isOpen, patchNotes.isOpen]);

  // ── Sidebar swipe (disabled when overlays open) ──
  const anyOverlayOpenRef = useRef(false);
  anyOverlayOpenRef.current = anyOverlayOpen;

  const guardedSidebarOpen = useCallback(() => {
    if (!anyOverlayOpenRef.current) sidebar.open();
  }, [sidebar]);
  const guardedSidebarClose = useCallback(() => {
    if (!anyOverlayOpenRef.current) sidebar.close();
  }, [sidebar]);

  const swipeHandlers = useSwipe({
    onSwipeRight: guardedSidebarOpen,
    onSwipeLeft: guardedSidebarClose,
  });

  // ── Overlay swipe carousel (mobile only) ──
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches
  );
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)');
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const [carouselIdx, setCarouselIdx] = useState(-1);
  const [dragPx, setDragPx] = useState(0);
  const [smooth, setSmooth] = useState(false);
  const transitioningRef = useRef(false);
  const stripRef = useRef(null);
  const touchRef = useRef(null);
  const dragRef = useRef(0); // mirror of dragPx for sync reads in handlers

  // Sync carousel position with active overlay (toolbar opens)
  useEffect(() => {
    if (transitioningRef.current) return;
    if (!isMobile) { setCarouselIdx(-1); return; }
    if (activeOverlayId) {
      const idx = overlaySequence.findIndex(o => o.id === activeOverlayId);
      setCarouselIdx(idx);
    } else {
      setCarouselIdx(-1);
    }
  }, [isMobile, activeOverlayId, overlaySequence]);

  // Close carousel on Escape
  useEffect(() => {
    if (!isMobile || carouselIdx < 0) return;
    const handler = (e) => { if (e.key === 'Escape') closeAllOverlays(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isMobile, carouselIdx, closeAllOverlays]);

  const handleCarouselTouchStart = useCallback((e) => {
    if (smooth) return;
    // Don't hijack touch from interactive controls (sliders, selects, etc.)
    const tag = e.target.tagName;
    const type = e.target.type;
    if (tag === 'INPUT' && (type === 'range' || type === 'number') || tag === 'SELECT' || tag === 'TEXTAREA') return;
    const t = e.touches[0];
    touchRef.current = { x: t.clientX, y: t.clientY, dragging: false };
  }, [smooth]);

  const handleCarouselTouchMove = useCallback((e) => {
    if (!touchRef.current) return;
    const t = e.touches[0];
    const dx = t.clientX - touchRef.current.x;
    const dy = t.clientY - touchRef.current.y;

    if (!touchRef.current.dragging) {
      if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        const canPrev = carouselIdx > 0;
        const canNext = carouselIdx < overlaySequence.length - 1;
        if ((dx > 0 && canPrev) || (dx < 0 && canNext)) {
          touchRef.current.dragging = true;
        } else {
          touchRef.current = null;
          return;
        }
      } else {
        return;
      }
    }

    const canPrev = carouselIdx > 0;
    const canNext = carouselIdx < overlaySequence.length - 1;
    let clamped = dx;
    if (dx > 0 && !canPrev) clamped = 0;
    if (dx < 0 && !canNext) clamped = 0;
    dragRef.current = clamped;
    setDragPx(clamped);
  }, [carouselIdx, overlaySequence.length]);

  const handleCarouselTouchEnd = useCallback(() => {
    if (!touchRef.current?.dragging) { touchRef.current = null; return; }

    const dx = dragRef.current;
    const threshold = window.innerWidth * 0.25;
    let targetIdx = carouselIdx;

    if (dx > threshold && carouselIdx > 0) {
      targetIdx = carouselIdx - 1;
    } else if (dx < -threshold && carouselIdx < overlaySequence.length - 1) {
      targetIdx = carouselIdx + 1;
    }

    if (dx === 0 && targetIdx === carouselIdx) {
      touchRef.current = null;
      return;
    }

    transitioningRef.current = true;
    dragRef.current = 0;
    setDragPx(0);
    setSmooth(true);
    setCarouselIdx(targetIdx);
    touchRef.current = null;

    // Fallback if transitionEnd does not fire (e.g. no visual change)
    setTimeout(() => {
      if (transitioningRef.current) finaliseCarouselSwipe(targetIdx);
    }, 400);
  }, [carouselIdx, overlaySequence.length]);

  const finaliseCarouselSwipe = useCallback((targetIdx) => {
    if (!transitioningRef.current) return;
    setSmooth(false);
    const targetId = overlaySequence[targetIdx]?.id;
    if (targetId && targetId !== activeOverlayId) {
      closeAllOverlays();
      overlaySequence[targetIdx].hook.open();
    }
    transitioningRef.current = false;
  }, [overlaySequence, activeOverlayId, closeAllOverlays]);

  const handleCarouselTransitionEnd = useCallback(() => {
    finaliseCarouselSwipe(carouselIdx);
  }, [carouselIdx, finaliseCarouselSwipe]);

  // ── Cortex progress + update indicator ──
  const [cortexUpdating, setCortexUpdating] = useState(false);
  const [cortexProgress, setCortexProgress] = useState(null);
  const cortexTimerRef = useRef(null);

  useEffect(() => {
    const handleCortexProgress = (e) => {
      const { triggered, progress, frequency } = e.detail;

      // Always update progress bar data
      if (triggered) {
        // Reset to 0 on trigger, then update with post-reset progress
        setCortexProgress({ ...progress, progress_percent: 0, frequency });
      } else {
        setCortexProgress({ ...progress, frequency });
      }

      // Show indicator only when triggered
      if (triggered) {
        setCortexUpdating(true);
        clearTimeout(cortexTimerRef.current);
        cortexTimerRef.current = setTimeout(() => {
          setCortexUpdating(false);
        }, 8000);
      }
    };

    window.addEventListener('cortex-progress', handleCortexProgress);
    return () => {
      window.removeEventListener('cortex-progress', handleCortexProgress);
      clearTimeout(cortexTimerRef.current);
    };
  }, []);

  // ── Auto-open error overlays on chat errors ──
  useEffect(() => {
    if (!error) return;
    if (error.type === 'credit_balance_exhausted' || error.type === 'credit_exhausted') {
      creditExhausted.open();
    } else if (error.type === 'api_key_missing') {
      apiWarning.open();
    }
  }, [error]);

  const handleOpenAvatarEditor = useCallback((target = 'persona') => {
    setAvatarTarget(target);
    avatarEditor.open();
  }, [avatarEditor]);

  // Render the correct overlay content for a carousel slot
  const renderCarouselPanel = useCallback((id, isOpen) => {
    switch (id) {
      case 'userProfile':
        return <UserProfileOverlay panelOnly open={isOpen} onClose={closeAllOverlays} onOpenAvatarEditor={() => handleOpenAvatarEditor('user')} avatarRefreshKey={avatarRefreshKey} />;
      case 'apiKey':
        return <ApiKeyOverlay panelOnly open={isOpen} onClose={closeAllOverlays} />;
      case 'cortex':
        return <CortexOverlay panelOnly open={isOpen} onClose={closeAllOverlays} />;
      case 'personaSettings':
        return <PersonaSettingsOverlay panelOnly open={isOpen} onClose={closeAllOverlays} onOpenAvatarEditor={handleOpenAvatarEditor} onOpenCustomSpecs={() => { closeAllOverlays(); customSpecs.open(); }} avatarCallbackRef={personaAvatarCallbackRef} />;
      case 'interfaceSettings':
        return <InterfaceSettingsOverlay panelOnly open={isOpen} onClose={closeAllOverlays} />;
      case 'apiSettings':
        return <ApiSettingsOverlay panelOnly open={isOpen} onClose={closeAllOverlays} />;
      case 'support':
        return <SupportOverlay panelOnly open={isOpen} onClose={closeAllOverlays} />;
      case 'patchNotes':
        return <PatchNotesOverlay panelOnly open={isOpen} onClose={closeAllOverlays} />;
      default:
        return null;
    }
  }, [closeAllOverlays, handleOpenAvatarEditor, avatarRefreshKey, personaAvatarCallbackRef, customSpecs]);

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

  // ── Send message + pass pending afterthought context ──
  const handleSend = useCallback((text) => {
    const pendingThought = consumePendingThought();
    sendMessage(text, { pendingAfterthought: pendingThought });
    onAfterthoughtMessage();
  }, [sendMessage, onAfterthoughtMessage, consumePendingThought]);

  // ── New chat ──
  const handleNewChat = useCallback(async () => {
    try {
      const result = await createSession(personaId);
      sidebar.close();
      
      // Trigger auto first message if enabled
      if (result?.auto_first_message) {
        triggerAutoFirstMessage(result.session_id, result.persona_id || personaId);
      }
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  }, [personaId, createSession, sidebar, triggerAutoFirstMessage]);

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
        anyOverlayOpen={anyOverlayOpen}
        activeOverlayId={activeOverlayId}
        onToggleSidebar={sidebar.toggle}
        onOpenPersonaSettings={() => openExclusive(personaSettings)}
        onOpenInterfaceSettings={() => openExclusive(interfaceSettings)}
        onOpenApiKey={() => openExclusive(apiKey)}
        onOpenApiSettings={() => openExclusive(apiSettings)}
        onOpenServerSettings={() => openExclusive(serverSettings)}
        onOpenCortex={() => openExclusive(cortex)}
        onOpenUserProfile={() => openExclusive(userProfile)}
        onOpenQRCode={() => openExclusive(qrCode)}
        onOpenAccessControl={() => openExclusive(accessControl)}
        onOpenSupport={() => openExclusive(support)}
        onOpenPatchNotes={() => openExclusive(patchNotes)}
      />

      <div style={{ position: 'relative', height: 0, zIndex: 50 }}>
        <ContextBar cortexProgress={cortexProgress} />
      </div>

      {cortexUpdating && <CortexUpdateIndicator />}

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
        onDeleteLast={deleteLastMsg}
        onEditLast={editLastMsg}
        onRegenerateLast={regenerateLastMsg}
        onResendLast={resendLastMsg}
      />

      <ChatInput
        onSend={handleSend}
        disabled={!sessionId}
        isStreaming={isStreaming}
        onCancel={cancelStream}
        sessionId={sessionId}
      />

      {/* ── Swipeable overlays: carousel on mobile, individual on desktop ── */}
      {isMobile ? (
        carouselIdx >= 0 && (
          <div className={styles.carouselBackdrop}>
            <div
              ref={stripRef}
              className={`${styles.carouselStrip} ${smooth ? styles.carouselSmooth : ''}`}
              style={{ transform: `translateX(calc(${-carouselIdx * 100}vw + ${dragPx}px))` }}
              onTouchStart={handleCarouselTouchStart}
              onTouchMove={handleCarouselTouchMove}
              onTouchEnd={handleCarouselTouchEnd}
              onTransitionEnd={handleCarouselTransitionEnd}
            >
              {overlaySequence.map((item, i) => (
                <div key={item.id} className={styles.carouselSlot}>
                  {Math.abs(i - carouselIdx) <= 1
                    ? renderCarouselPanel(item.id, item.hook.isOpen)
                    : null}
                </div>
              ))}
            </div>
          </div>
        )
      ) : (
        <>
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
          <CortexOverlay
            open={cortex.isOpen}
            onClose={cortex.close}
          />
          <UserProfileOverlay
            open={userProfile.isOpen}
            onClose={userProfile.close}
            onOpenAvatarEditor={() => handleOpenAvatarEditor('user')}
            avatarRefreshKey={avatarRefreshKey}
          />
          <AccessControlOverlay
            open={accessControl.isOpen}
            onClose={accessControl.close}
          />
          <SupportOverlay
            open={support.isOpen}
            onClose={support.close}
          />
          <PatchNotesOverlay
            open={patchNotes.isOpen}
            onClose={patchNotes.close}
          />
        </>
      )}

      {/* ── Non-swipeable overlays (always individual with own backdrop) ── */}
      <AvatarEditorOverlay
        open={avatarEditor.isOpen}
        onClose={avatarEditor.close}
        personaId={personaId}
        target={avatarTarget}
        onSaved={handleAvatarSaved}
        stacked
      />
      <CustomSpecsOverlay
        open={customSpecs.isOpen}
        onClose={customSpecs.close}
        onOpenList={() => { customSpecs.close(); customSpecsList.open(); }}
      />
      <CustomSpecsListOverlay
        open={customSpecsList.isOpen}
        onClose={customSpecsList.close}
        onOpenCreate={() => { customSpecsList.close(); customSpecs.open(); }}
      />
      <QRCodeOverlay
        open={qrCode.isOpen}
        onClose={qrCode.close}
        onOpenServerSettings={() => { qrCode.close(); serverSettings.open(); }}
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
      <AccessNotification polling={qrCode.isOpen} />
    </div>
  );
}
