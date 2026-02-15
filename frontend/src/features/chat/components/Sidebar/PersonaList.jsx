// ── PersonaList Component ──
// Loads persona summary for session counts and last activity, sorts like legacy

import { useState, useEffect, useMemo } from 'react';
import { getPersonaSummary } from '../../../../services/sessionApi';
import PersonaCard from './PersonaCard';
import styles from './Sidebar.module.css';

export default function PersonaList({ personas, activePersonaId, onSelectPersona }) {
  const [summary, setSummary] = useState({});

  // Load persona summary (session counts + last_updated)
  useEffect(() => {
    getPersonaSummary()
      .then((data) => {
        if (data.success && data.summary) {
          const map = {};
          data.summary.forEach((s) => {
            map[s.persona_id] = {
              session_count: s.session_count,
              last_updated: s.last_updated,
            };
          });
          setSummary(map);
        }
      })
      .catch(() => {});
  }, []);

  // Merge summary into personas and sort: active first, then by last_updated DESC
  const enrichedPersonas = useMemo(() => {
    const merged = (personas || []).map((p) => ({
      ...p,
      session_count: summary[p.id]?.session_count || 0,
      last_updated: summary[p.id]?.last_updated || null,
    }));

    merged.sort((a, b) => {
      if (a.id === activePersonaId) return -1;
      if (b.id === activePersonaId) return 1;
      const aTime = a.last_updated || '';
      const bTime = b.last_updated || '';
      return bTime.localeCompare(aTime);
    });

    return merged;
  }, [personas, summary, activePersonaId]);

  if (!enrichedPersonas.length) {
    return <div className={styles.empty}>Keine Personas vorhanden</div>;
  }

  return (
    <div className={styles.list}>
      {enrichedPersonas.map((persona) => (
        <PersonaCard
          key={persona.id}
          persona={persona}
          isActive={persona.id === activePersonaId}
          onClick={() => onSelectPersona(persona.id)}
        />
      ))}
    </div>
  );
}
