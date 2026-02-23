// ── Header Component ──

import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useSession } from '../../../../hooks/useSession';
import { useSettings } from '../../../../hooks/useSettings';
import Avatar from '../../../../components/Avatar/Avatar';
import { checkApiStatus } from '../../../../services/serverApi';
import { playNotificationSound } from '../../../../utils/audioUtils';
import { useLanguage } from '../../../../hooks/useLanguage';
import styles from './Header.module.css';

// ── SVG Icons ──
import {
  SoundOnIcon, SoundOffIcon, QRCodeIcon,
  UserIcon, KeyIcon, CortexIcon, PersonaIcon, GearIcon,
  MonitorIcon, ChatIcon, ServerIcon, ShieldIcon,
  GitHubIcon, ExternalLinkIcon, HeartIcon, BugIcon, PatchNotesIcon,
} from '../../../../components/Icons/Icons';

export default function Header({
  anyOverlayOpen = false,
  activeOverlayId = null,
  onToggleSidebar,
  onOpenPersonaSettings,
  onOpenInterfaceSettings,
  onOpenApiKey,
  onOpenApiSettings,
  onOpenServerSettings,
  onOpenCortex,
  onOpenUserProfile,
  onOpenQRCode,
  onOpenAccessControl,
  onOpenSupport,
  onOpenPatchNotes,
}) {
  const { character, sessionId } = useSession();
  const { get, set } = useSettings();
  const { t } = useLanguage();
  const h = t('header');

  const charName = character?.char_name || 'PersonaUI';
  const charAvatar = character?.avatar;
  const charAvatarType = character?.avatar_type;

  // ── Sound toggle state ──
  const soundEnabled = get('notificationSound', false);
  const notificationVolume = get('notificationVolume', 0.5);
  const toggleSound = useCallback(() => {
    const newState = !soundEnabled;
    set('notificationSound', newState);
    // Play preview sound when turning ON
    if (newState) {
      playNotificationSound(notificationVolume);
    }
  }, [soundEnabled, notificationVolume, set]);

  // ── Volume slider (long-hover popup) ──
  const [volumeSliderVisible, setVolumeSliderVisible] = useState(false);
  const volumeHoverTimerRef = useRef(null);
  const volumeHideTimerRef = useRef(null);
  const soundBtnRef = useRef(null);

  const handleSoundMouseEnter = useCallback(() => {
    if (volumeHideTimerRef.current) {
      clearTimeout(volumeHideTimerRef.current);
      volumeHideTimerRef.current = null;
    }
    // Show slider after 600ms hover ("long hover")
    volumeHoverTimerRef.current = setTimeout(() => {
      setVolumeSliderVisible(true);
    }, 600);
  }, []);

  const handleSoundMouseLeave = useCallback(() => {
    if (volumeHoverTimerRef.current) {
      clearTimeout(volumeHoverTimerRef.current);
      volumeHoverTimerRef.current = null;
    }
    // Hide slider after a short delay
    volumeHideTimerRef.current = setTimeout(() => {
      setVolumeSliderVisible(false);
    }, 400);
  }, []);

  const handleVolumeChange = useCallback((e) => {
    const newVol = parseFloat(e.target.value);
    set('notificationVolume', newVol);
    // Enable sound if adjusting volume
    if (!soundEnabled) set('notificationSound', true);
  }, [set, soundEnabled]);

  const handleVolumeSliderMouseUp = useCallback(() => {
    // Play preview on release so user hears the new level
    playNotificationSound(get('notificationVolume', 0.5));
  }, [get]);

  // Cleanup volume timers
  useEffect(() => {
    return () => {
      if (volumeHoverTimerRef.current) clearTimeout(volumeHoverTimerRef.current);
      if (volumeHideTimerRef.current) clearTimeout(volumeHideTimerRef.current);
    };
  }, []);

  // ── Toolbar visibility (hamburger toggle) ──
  const [toolbarVisible, setToolbarVisible] = useState(false);
  const headerRef = useRef(null);
  const hideTimerRef = useRef(null);

  const toggleToolbar = useCallback(() => {
    setToolbarVisible(prev => !prev);
  }, []);

  // Auto-hide: start 2s timer when mouse leaves the entire header area
  const handleHeaderMouseEnter = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const handleHeaderMouseLeave = useCallback(() => {
    if (toolbarVisible) {
      hideTimerRef.current = setTimeout(() => {
        setToolbarVisible(false);
        setSettingsOpen(false);
      }, 2000);
    }
  }, [toolbarVisible]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      if (settingsTimerRef.current) clearTimeout(settingsTimerRef.current);
      if (communityTimerRef.current) clearTimeout(communityTimerRef.current);
    };
  }, []);

  // ── Click outside header → close toolbar ──
  const portalRef = useRef(null);
  useEffect(() => {
    if (!toolbarVisible) return;
    const handleClickOutside = (e) => {
      if (
        headerRef.current && !headerRef.current.contains(e.target) &&
        (!portalRef.current || !portalRef.current.contains(e.target)) &&
        (!communityPortalRef.current || !communityPortalRef.current.contains(e.target))
      ) {
        setToolbarVisible(false);
        setSettingsOpen(false);
        setCommunityOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [toolbarVisible]);

  // ── Hover capability detection (no hover = touch device) ──
  const canHover = useRef(
    typeof window !== 'undefined' && window.matchMedia('(hover: hover)').matches
  );

  // ── Mobile detection ──
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches
  );
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)');
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // ── Settings submenu state (with hover delay) ──
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef(null);
  const settingsTimerRef = useRef(null);

  const handleSettingsEnter = useCallback(() => {
    if (!canHover.current) return;
    if (settingsTimerRef.current) {
      clearTimeout(settingsTimerRef.current);
      settingsTimerRef.current = null;
    }
    setSettingsOpen(true);
  }, []);

  const handleSettingsLeave = useCallback(() => {
    if (!canHover.current) return;
    settingsTimerRef.current = setTimeout(() => {
      setSettingsOpen(false);
    }, 400);
  }, []);

  const handleSettingsClick = useCallback(() => {
    setSettingsOpen(prev => {
      if (!prev) setCommunityOpen(false);
      return !prev;
    });
  }, []);

  // ── Community submenu state (with hover delay) ──
  const [communityOpen, setCommunityOpen] = useState(false);
  const communityRef = useRef(null);
  const communityTimerRef = useRef(null);
  const communityPortalRef = useRef(null);

  const handleCommunityEnter = useCallback(() => {
    if (!canHover.current) return;
    if (communityTimerRef.current) {
      clearTimeout(communityTimerRef.current);
      communityTimerRef.current = null;
    }
    setCommunityOpen(true);
  }, []);

  const handleCommunityLeave = useCallback(() => {
    if (!canHover.current) return;
    communityTimerRef.current = setTimeout(() => {
      setCommunityOpen(false);
    }, 400);
  }, []);

  const handleCommunityClick = useCallback(() => {
    setCommunityOpen(prev => {
      if (!prev) setSettingsOpen(false);
      return !prev;
    });
  }, [])

  // ── API Status ──
  const [apiConnected, setApiConnected] = useState(null); // null=loading, true=connected, false=disconnected

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const data = await checkApiStatus();
        if (mounted) setApiConnected(!!data?.has_api_key);
      } catch {
        if (mounted) setApiConnected(false);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <header
      className={styles.header}
      ref={headerRef}
      onMouseEnter={handleHeaderMouseEnter}
      onMouseLeave={handleHeaderMouseLeave}
    >
      <div className={`${styles.headerContent} ${(toolbarVisible || anyOverlayOpen) ? styles.headerContentCollapsed : ''}`}>
        {/* ── Left: Avatar + Name ── */}
        <div className={styles.left}>
          <div className={styles.characterInfo} onClick={onToggleSidebar}>
            <Avatar
              src={charAvatar}
              type={charAvatarType}
              name={charName}
              size={48}
            />
            <h2 className={styles.characterName}>{charName}</h2>
          </div>
        </div>

        {/* ── Center: Logo ── */}
        <div className={styles.center}>
          <div className={styles.logo}>PERSONA UI</div>
        </div>

        {/* ── Right: Actions ── */}
        <div className={styles.right}>
          {/* Sound Toggle with Volume Slider */}
          <div
            className={styles.soundToggleWrap}
            onMouseEnter={handleSoundMouseEnter}
            onMouseLeave={handleSoundMouseLeave}
            ref={soundBtnRef}
          >
            <button
              className={`${styles.soundToggle} ${!soundEnabled ? styles.soundMuted : ''}`}
              onClick={toggleSound}
              title={h.soundToggle}
            >
              {soundEnabled ? <SoundOnIcon /> : <SoundOffIcon />}
            </button>

            {/* Volume slider popup (long-hover) */}
            {volumeSliderVisible && (
              <div
                className={styles.volumePopup}
                onMouseEnter={() => {
                  if (volumeHideTimerRef.current) {
                    clearTimeout(volumeHideTimerRef.current);
                    volumeHideTimerRef.current = null;
                  }
                }}
                onMouseLeave={handleSoundMouseLeave}
              >
                <div className={styles.volumePopupInner}>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={notificationVolume}
                    onChange={handleVolumeChange}
                    onMouseUp={handleVolumeSliderMouseUp}
                    className={styles.volumeSlider}
                    title={`${h.volume} ${Math.round(notificationVolume * 100)}%`}
                  />
                  <span className={styles.volumeLabel}>{Math.round(notificationVolume * 100)}%</span>
                </div>
              </div>
            )}
          </div>

          {/* QR Code Button */}
          <button
            className={styles.qrCodeBtn}
            onClick={onOpenQRCode}
            title={h.qrTitle}
          >
            <QRCodeIcon />
          </button>

          {/* API Status Indicator */}
          <div
            className={`${styles.apiStatus} ${apiConnected === true ? styles.apiConnected : apiConnected === false ? styles.apiDisconnected : ''}`}
            title={apiConnected === true ? h.apiConnected : apiConnected === false ? h.apiDisconnected : h.apiLoading}
          >
            <span className={styles.statusDot} />
          </div>

          {/* Hamburger toggle for toolbar */}
          <button
            className={`${styles.dropdownToggle} ${toolbarVisible ? styles.dropdownToggleActive : ''}`}
            onClick={toggleToolbar}
            title={h.menu}
          >
            ☰
          </button>
        </div>
      </div>

      {/* ── Toolbar: Centered icon bar below header ── */}
      <nav className={`${styles.toolbar} ${(toolbarVisible || anyOverlayOpen) ? styles.toolbarVisible : ''}`}>
        <div className={styles.toolbarInner}>
          <button
            className={`${styles.toolbarBtn} ${activeOverlayId === 'userProfile' ? styles.toolbarBtnActive : ''}`}
            onClick={onOpenUserProfile}
            title={h.profileBtn}
          >
            <UserIcon />
            <span className={styles.toolbarLabel}>{h.profileBtn}</span>
          </button>

          <button
            className={`${styles.toolbarBtn} ${activeOverlayId === 'apiKey' ? styles.toolbarBtnActive : ''}`}
            onClick={onOpenApiKey}
            title="Set API-Key"
          >
            <KeyIcon />
            <span className={styles.toolbarLabel}>{h.apiKeyBtn}</span>
          </button>

          <button
            className={`${styles.toolbarBtn} ${activeOverlayId === 'cortex' ? styles.toolbarBtnActive : ''}`}
            onClick={onOpenCortex}
            title="Cortex"
          >
            <CortexIcon />
            <span className={styles.toolbarLabel}>{h.cortexBtn}</span>
          </button>

          <button
            className={`${styles.toolbarBtn} ${activeOverlayId === 'personaSettings' ? styles.toolbarBtnActive : ''}`}
            onClick={onOpenPersonaSettings}
            title="Persona"
          >
            <PersonaIcon />
            <span className={styles.toolbarLabel}>{h.personaBtn}</span>
          </button>

          {/* Settings with hover submenu */}
          <div
            className={styles.settingsGroup}
            ref={settingsRef}
            onMouseEnter={handleSettingsEnter}
            onMouseLeave={handleSettingsLeave}
          >
            <button
              className={`${styles.toolbarBtn} ${settingsOpen ? styles.toolbarBtnActive : ''} ${['interfaceSettings', 'apiSettings', 'serverSettings', 'accessControl'].includes(activeOverlayId) ? styles.toolbarBtnActive : ''}`}
              title="Settings"
              onClick={handleSettingsClick}
            >
              <GearIcon />
              <span className={styles.toolbarLabel}>{h.settingsBtn}</span>
            </button>
          </div>

          {/* Community with hover submenu */}
          <div
            className={styles.settingsGroup}
            ref={communityRef}
            onMouseEnter={handleCommunityEnter}
            onMouseLeave={handleCommunityLeave}
          >
            <button
              className={`${styles.toolbarBtn} ${communityOpen ? styles.toolbarBtnActive : ''} ${['support', 'patchNotes'].includes(activeOverlayId) ? styles.toolbarBtnActive : ''}`}
              title="Community & Support"
              onClick={handleCommunityClick}
            >
              <GitHubIcon />
              <span className={styles.toolbarLabel}>{h.communityBtn}</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Portal: Settings submenu */}
      {settingsOpen && createPortal(
        <div
          ref={portalRef}
          className={styles.settingsPortal}
          style={{
            top: settingsRef.current
              ? settingsRef.current.getBoundingClientRect().bottom + window.scrollY + 'px'
              : '0px',
            left: settingsRef.current
              ? settingsRef.current.getBoundingClientRect().left + settingsRef.current.offsetWidth / 2 + 'px'
              : '0px',
          }}
          onMouseEnter={handleSettingsEnter}
          onMouseLeave={handleSettingsLeave}
        >
          <div className={styles.settingsSubmenuInner}>
            <div className={styles.submenuBackdrop} aria-hidden="true" />
            <div className={styles.submenuContent}>
              <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenInterfaceSettings?.(); }}>
                <MonitorIcon />
                <span>{h.interfaceSubmenu}</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenApiSettings?.(); }}>
                <ChatIcon />
                <span>{h.apiChatSubmenu}</span>
              </button>
              {!isMobile && (
                <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenServerSettings?.(); }}>
                  <ServerIcon />
                  <span>{h.serverSubmenu}</span>
                </button>
              )}
              {!isMobile && (
                <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenAccessControl?.(); }}>
                  <ShieldIcon />
                  <span>{h.accessSubmenu}</span>
                </button>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Portal: Community submenu */}
      {communityOpen && createPortal(
        <div
          ref={communityPortalRef}
          className={styles.settingsPortal}
          style={{
            top: communityRef.current
              ? communityRef.current.getBoundingClientRect().bottom + window.scrollY + 'px'
              : '0px',
            left: communityRef.current
              ? communityRef.current.getBoundingClientRect().left + communityRef.current.offsetWidth / 2 + 'px'
              : '0px',
          }}
          onMouseEnter={handleCommunityEnter}
          onMouseLeave={handleCommunityLeave}
        >
          <div className={styles.settingsSubmenuInner}>
            <div className={styles.submenuBackdrop} aria-hidden="true" />
            <div className={styles.submenuContent}>
              <button className={styles.submenuBtn} onClick={() => { setCommunityOpen(false); window.open('https://github.com/Sakushi-Dev/PersonaUI', '_blank'); }}>
                <ExternalLinkIcon />
                <span>{h.githubSubmenu}</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setCommunityOpen(false); window.open('https://github.com/Sakushi-Dev/PersonaUI/issues', '_blank'); }}>
                <BugIcon />
                <span>{h.issuesSubmenu}</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setCommunityOpen(false); onOpenSupport?.(); }}>
                <HeartIcon />
                <span>{h.supportSubmenu}</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setCommunityOpen(false); onOpenPatchNotes?.(); }}>
                <PatchNotesIcon />
                <span>{h.patchNotesSubmenu}</span>
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </header>
  );
}
