// ── useSidebar Hook ──

import { useState, useCallback } from 'react';
import * as storage from '../../../utils/storage';

export function useSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const [view, setView] = useState('personas'); // 'personas' | 'sessions'
  const [selectedPersonaId, setSelectedPersonaId] = useState(null);

  const toggle = useCallback(() => {
    setIsOpen((prev) => {
      const willOpen = !prev;
      storage.setItem('sidebarCollapsed', !willOpen);
      if (willOpen) {
        // Always start with personas view when opening
        setView('personas');
        setSelectedPersonaId(null);
      }
      return willOpen;
    });
  }, []);

  const open = useCallback(() => {
    setView('personas');
    setSelectedPersonaId(null);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    storage.setItem('sidebarCollapsed', true);
  }, []);

  const showPersonas = useCallback(() => {
    setView('personas');
    setSelectedPersonaId(null);
  }, []);

  const showSessions = useCallback((personaId) => {
    setView('sessions');
    setSelectedPersonaId(personaId);
  }, []);

  return {
    isOpen,
    view,
    selectedPersonaId,
    toggle,
    open,
    close,
    showPersonas,
    showSessions,
  };
}
