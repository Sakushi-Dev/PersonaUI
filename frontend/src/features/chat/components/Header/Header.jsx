// ── Header Component ──

import { useState, useEffect, useCallback } from 'react';
import { useSession } from '../../../../hooks/useSession';
import { useSettings } from '../../../../hooks/useSettings';
import Avatar from '../../../../components/Avatar/Avatar';
import Dropdown from '../../../../components/Dropdown/Dropdown';
import DropdownItem from '../../../../components/Dropdown/DropdownItem';
import DropdownSubmenu from '../../../../components/Dropdown/DropdownSubmenu';
import { checkApiStatus } from '../../../../services/serverApi';
import { checkMemoryAvailability } from '../../../../services/memoryApi';
import styles from './Header.module.css';

// ── SVG Icons ──
function SoundOnIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  );
}

function SoundOffIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <line x1="23" y1="9" x2="17" y2="15" />
      <line x1="17" y1="9" x2="23" y2="15" />
    </svg>
  );
}

function QRCodeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="3" width="7" height="7" stroke="currentColor" strokeWidth="2" />
      <rect x="14" y="3" width="7" height="7" stroke="currentColor" strokeWidth="2" />
      <rect x="3" y="14" width="7" height="7" stroke="currentColor" strokeWidth="2" />
      <rect x="5" y="5" width="3" height="3" fill="currentColor" />
      <rect x="16" y="5" width="3" height="3" fill="currentColor" />
      <rect x="5" y="16" width="3" height="3" fill="currentColor" />
      <rect x="14" y="14" width="3" height="3" fill="currentColor" />
      <rect x="18" y="14" width="3" height="3" fill="currentColor" />
      <rect x="14" y="18" width="3" height="3" fill="currentColor" />
    </svg>
  );
}

export default function Header({
  onToggleSidebar,
  onOpenPersonaSettings,
  onOpenInterfaceSettings,
  onOpenApiKey,
  onOpenApiSettings,
  onOpenServerSettings,
  onOpenMemory,
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

  // ── Memory availability ──
  const [memoryState, setMemoryState] = useState({ available: false, warning: false, critical: false });

  useEffect(() => {
    if (!sessionId) return;
    let mounted = true;
    const check = async () => {
      try {
        const data = await checkMemoryAvailability(sessionId);
        if (mounted && data?.success) {
          setMemoryState({
            available: !!data.available,
            warning: !!data.context_limit_warning,
            critical: !!data.context_limit_critical,
          });
        }
      } catch {
        // ignore
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { mounted = false; clearInterval(interval); };
  }, [sessionId]);

  const memoryBtnClass = [
    styles.memoryBtn,
    !memoryState.available ? styles.memoryDisabled : '',
    memoryState.critical ? styles.memoryCritical : '',
    !memoryState.critical && memoryState.warning ? styles.memoryWarning : '',
  ].filter(Boolean).join(' ');

  const handleMemoryClick = useCallback(() => {
    if (memoryState.available) {
      onOpenMemory?.();
    }
  }, [memoryState.available, onOpenMemory]);

  return (
    <header className={styles.header}>
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
          {/* Memory Button */}
          <button
            className={memoryBtnClass}
            onClick={handleMemoryClick}
            title={memoryState.available
              ? (memoryState.critical
                ? 'Erinnerung dringend empfohlen – Kontextlimit fast erreicht!'
                : memoryState.warning
                  ? 'Erinnerung empfohlen – Kontextlimit wird bald erreicht'
                  : 'Erinnerung erstellen')
              : 'Erinnerung erstellen (ab 3 Nachrichten)'}
          >
            Erinnern
          </button>

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

          {/* Settings Dropdown (☰ hamburger like legacy) */}
          <Dropdown
            trigger={
              <button className={styles.dropdownToggle} title="Einstellungen">
                ☰
              </button>
            }
          >
            {(close) => (
              <>
                <DropdownItem label="Mein Profil" onClick={() => { close(); onOpenUserProfile?.(); }} />
                <DropdownItem label="Set API-Key" onClick={() => { close(); onOpenApiKey?.(); }} />
                <DropdownItem label="Erinnerungen" onClick={() => { close(); onOpenMemory?.(); }} />
                <DropdownItem label="Persona" onClick={() => { close(); onOpenPersonaSettings?.(); }} />
                <DropdownSubmenu label="Einstellungen">
                  <DropdownItem label="Interface" onClick={() => { close(); onOpenInterfaceSettings?.(); }} />
                  <DropdownItem label="API / Chat" onClick={() => { close(); onOpenApiSettings?.(); }} />
                  <DropdownItem label="Server" onClick={() => { close(); onOpenServerSettings?.(); }} />
                  <DropdownItem label="Zugangskontrolle" onClick={() => { close(); onOpenAccessControl?.(); }} />
                </DropdownSubmenu>
              </>
            )}
          </Dropdown>
        </div>
      </div>
    </header>
  );
}
