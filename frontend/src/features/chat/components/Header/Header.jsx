// ── Header Component ──

import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useSession } from '../../../../hooks/useSession';
import { useSettings } from '../../../../hooks/useSettings';
import Avatar from '../../../../components/Avatar/Avatar';
import { checkApiStatus } from '../../../../services/serverApi';
import styles from './Header.module.css';

// ── SVG Icons ──
import {
  SoundOnIcon, SoundOffIcon, QRCodeIcon,
  UserIcon, KeyIcon, CortexIcon, PersonaIcon, GearIcon,
  MonitorIcon, ChatIcon, ServerIcon, ShieldIcon,
} from '../../../../components/Icons/Icons';

export default function Header({
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
}) {
  const { character, sessionId } = useSession();
  const { get, set } = useSettings();

  const charName = character?.char_name || 'PersonaUI';
  const charAvatar = character?.avatar;
  const charAvatarType = character?.avatar_type;

  // ── Sound toggle state ──
  const soundEnabled = get('notificationSound', false);
  const toggleSound = useCallback(() => {
    set('notificationSound', !soundEnabled);
  }, [soundEnabled, set]);

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
    };
  }, []);

  // ── Click outside header → close toolbar ──
  const portalRef = useRef(null);
  useEffect(() => {
    if (!toolbarVisible) return;
    const handleClickOutside = (e) => {
      if (
        headerRef.current && !headerRef.current.contains(e.target) &&
        (!portalRef.current || !portalRef.current.contains(e.target))
      ) {
        setToolbarVisible(false);
        setSettingsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [toolbarVisible]);

  // ── Settings submenu state (with hover delay) ──
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef(null);
  const settingsTimerRef = useRef(null);

  const handleSettingsEnter = useCallback(() => {
    if (settingsTimerRef.current) {
      clearTimeout(settingsTimerRef.current);
      settingsTimerRef.current = null;
    }
    setSettingsOpen(true);
  }, []);

  const handleSettingsLeave = useCallback(() => {
    settingsTimerRef.current = setTimeout(() => {
      setSettingsOpen(false);
    }, 400);
  }, []);

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
      <div className={styles.headerContent}>
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
          {/* Sound Toggle */}
          <button
            className={`${styles.soundToggle} ${!soundEnabled ? styles.soundMuted : ''}`}
            onClick={toggleSound}
            title="Benachrichtigungston an/aus"
          >
            {soundEnabled ? <SoundOnIcon /> : <SoundOffIcon />}
          </button>

          {/* QR Code Button */}
          <button
            className={styles.qrCodeBtn}
            onClick={onOpenQRCode}
            title="QR-Code & Netzwerk-Adressen"
          >
            <QRCodeIcon />
          </button>

          {/* API Status Indicator */}
          <div
            className={`${styles.apiStatus} ${apiConnected === true ? styles.apiConnected : apiConnected === false ? styles.apiDisconnected : ''}`}
            title={apiConnected === true ? 'Bestätigter API Zugang' : apiConnected === false ? 'API Zugang benötigt' : 'Lädt...'}
          >
            <span className={styles.statusDot} />
          </div>

          {/* Hamburger toggle for toolbar */}
          <button
            className={`${styles.dropdownToggle} ${toolbarVisible ? styles.dropdownToggleActive : ''}`}
            onClick={toggleToolbar}
            title="Menü"
          >
            ☰
          </button>
        </div>
      </div>

      {/* ── Toolbar: Centered icon bar below header ── */}
      <nav className={`${styles.toolbar} ${toolbarVisible ? styles.toolbarVisible : ''}`}>
        <div className={styles.toolbarInner}>
          <button
            className={styles.toolbarBtn}
            onClick={onOpenUserProfile}
            title="Mein Profil"
          >
            <UserIcon />
            <span className={styles.toolbarLabel}>Profil</span>
          </button>

          <button
            className={styles.toolbarBtn}
            onClick={onOpenApiKey}
            title="Set API-Key"
          >
            <KeyIcon />
            <span className={styles.toolbarLabel}>API-Key</span>
          </button>

          <button
            className={styles.toolbarBtn}
            onClick={onOpenCortex}
            title="Cortex"
          >
            <CortexIcon />
            <span className={styles.toolbarLabel}>Cortex</span>
          </button>

          <button
            className={styles.toolbarBtn}
            onClick={onOpenPersonaSettings}
            title="Persona"
          >
            <PersonaIcon />
            <span className={styles.toolbarLabel}>Persona</span>
          </button>

          {/* Settings with hover submenu */}
          <div
            className={styles.settingsGroup}
            ref={settingsRef}
            onMouseEnter={handleSettingsEnter}
            onMouseLeave={handleSettingsLeave}
          >
            <button
              className={styles.toolbarBtn}
              title="Einstellungen"
            >
              <GearIcon />
              <span className={styles.toolbarLabel}>Settings</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Portal: Submenu rendered outside header to allow backdrop-filter */}
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
                <span>Interface</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenApiSettings?.(); }}>
                <ChatIcon />
                <span>API / Chat</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenServerSettings?.(); }}>
                <ServerIcon />
                <span>Server</span>
              </button>
              <button className={styles.submenuBtn} onClick={() => { setSettingsOpen(false); onOpenAccessControl?.(); }}>
                <ShieldIcon />
                <span>Zugang</span>
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </header>
  );
}
