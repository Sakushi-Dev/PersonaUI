// ── MemoryOverlay ──
// Memory list grouped by category, create, edit, delete, toggle, stats

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSession } from '../../hooks/useSession';
import { useSettings } from '../../hooks/useSettings';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Toggle from '../../components/Toggle/Toggle';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import {
  getMemories,
  createMemory,
  previewMemory,
  updateMemory,
  deleteMemory,
  toggleMemory,
  checkMemoryAvailability,
  getMemoryStats,
} from '../../services/memoryApi';
import styles from './Overlays.module.css';

const MAX_MEMORIES = 30;

export default function MemoryOverlay({ open, onClose }) {
  const { sessionId, personaId } = useSession();
  const { get, set } = useSettings();

  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const memoriesEnabled = get('memoriesEnabled', true);

  // Preview state
  const [previewing, setPreviewing] = useState(false);
  const [previewText, setPreviewText] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [canCreate, setCanCreate] = useState(false);

  // Editing
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState('');

  // Collapsed categories
  const [collapsedCategories, setCollapsedCategories] = useState(new Set());

  // Stats
  const [stats, setStats] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [data, statsData] = await Promise.all([
        getMemories(),
        getMemoryStats().catch(() => null),
      ]);
      setMemories(data.memories || []);
      if (statsData) setStats(statsData);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      refresh();
      if (sessionId) {
        checkMemoryAvailability(sessionId).then((data) => {
          setCanCreate(data.available ?? false);
        }).catch(() => {});
      }
    } else {
      setShowPreview(false);
      setEditingId(null);
    }
  }, [open, sessionId, refresh]);

  // Group memories by category
  const groupedMemories = useMemo(() => {
    const groups = {};
    for (const mem of memories) {
      const cat = mem.category || 'Sonstige';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(mem);
    }
    return groups;
  }, [memories]);

  const activeCount = memories.filter((m) => m.active !== false).length;
  const inactiveCount = memories.length - activeCount;

  const toggleCategory = (cat) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const handlePreview = async () => {
    setPreviewing(true);
    setShowPreview(true);
    try {
      const data = await previewMemory({ session_id: sessionId });
      setPreviewText(data.content || data.preview || '');
    } catch {
      setPreviewText('Vorschau fehlgeschlagen.');
    } finally {
      setPreviewing(false);
    }
  };

  const handleSavePreview = async () => {
    try {
      await createMemory({ session_id: sessionId, content: previewText });
      setShowPreview(false);
      setPreviewText('');
      refresh();
    } catch (err) {
      console.error('Memory create failed:', err);
    }
  };

  const handleToggle = async (id) => {
    try {
      await toggleMemory(id);
      refresh();
    } catch {
      // silent
    }
  };

  const handleStartEdit = (mem) => {
    setEditingId(mem.id);
    setEditText(mem.content);
  };

  const handleSaveEdit = async () => {
    try {
      await updateMemory(editingId, { content: editText });
      setEditingId(null);
      refresh();
    } catch {
      // silent
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteMemory(id);
      refresh();
    } catch {
      // silent
    }
  };

  const handleDeleteAll = async () => {
    try {
      for (const mem of memories) {
        await deleteMemory(mem.id);
      }
      refresh();
    } catch {
      // silent
    }
  };

  const handleMemoriesEnabledChange = (val) => {
    set('memoriesEnabled', val);
  };

  // Preview modal
  if (showPreview) {
    return (
      <Overlay open={open} onClose={() => setShowPreview(false)} width="500px">
        <OverlayHeader title="💾 Neue Erinnerung" onClose={() => setShowPreview(false)} />
        <OverlayBody>
          {previewing ? (
            <div className={styles.centeredContent}>
              <Spinner />
              <p>Erinnerung wird erstellt...</p>
            </div>
          ) : (
            <textarea
              className={styles.textarea}
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
              rows={8}
            />
          )}
        </OverlayBody>
        <OverlayFooter>
          <Button variant="secondary" onClick={() => setShowPreview(false)}>Abbrechen</Button>
          <Button variant="secondary" onClick={handlePreview} disabled={previewing}>Wiederholen</Button>
          <Button variant="primary" onClick={handleSavePreview} disabled={previewing || !previewText}>
            Speichern
          </Button>
        </OverlayFooter>
      </Overlay>
    );
  }

  return (
    <Overlay open={open} onClose={onClose} width="540px">
      <OverlayHeader title="💾 Erinnerungen verwalten" onClose={onClose} />
      <OverlayBody>
        <div className={styles.settingRow}>
          <Toggle
            label={memoriesEnabled ? 'Aktiv' : 'Inaktiv'}
            checked={memoriesEnabled}
            onChange={handleMemoriesEnabledChange}
            id="memories-enabled"
          />
          <div className={styles.settingInfo}>
            <p className={styles.settingLabel}>Erinnerungen</p>
            <p className={styles.hint}>
              Aktive Erinnerungen werden automatisch in den Chat-Kontext eingebunden.
            </p>
          </div>
        </div>

        {/* Stats bar */}
        <div className={styles.statsBar}>
          <span>Gesamt: {memories.length}/{MAX_MEMORIES}</span>
          <span>Aktiv: {activeCount}</span>
          <span>Inaktiv: {inactiveCount}</span>
        </div>

        <div className={styles.listHeader}>
          <span>Erinnerungen</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {memories.length > 0 && (
              <Button variant="ghost" size="sm" onClick={handleDeleteAll}>
                Alle löschen
              </Button>
            )}
            {canCreate && memories.length < MAX_MEMORIES && (
              <Button variant="primary" size="sm" onClick={handlePreview}>
                + Erinnerung erstellen
              </Button>
            )}
          </div>
        </div>

        {loading ? (
          <Spinner />
        ) : memories.length === 0 ? (
          <p className={styles.emptyText}>Noch keine Erinnerungen vorhanden.</p>
        ) : (
          <div className={styles.categoryGroups}>
            {Object.entries(groupedMemories).map(([category, mems]) => (
              <div key={category} className={styles.categoryGroup}>
                <button
                  className={styles.categoryHeader}
                  onClick={() => toggleCategory(category)}
                >
                  <span>{collapsedCategories.has(category) ? '▶' : '▼'} {category}</span>
                  <span className={styles.badge}>{mems.length}</span>
                </button>

                {!collapsedCategories.has(category) && (
                  <ul className={styles.memoryList}>
                    {mems.map((mem) => (
                      <li key={mem.id} className={styles.memoryItem}>
                        {editingId === mem.id ? (
                          <div className={styles.editArea}>
                            <textarea
                              className={styles.textarea}
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              rows={4}
                            />
                            <div className={styles.editActions}>
                              <Button size="sm" variant="secondary" onClick={() => setEditingId(null)}>
                                Abbrechen
                              </Button>
                              <Button size="sm" variant="primary" onClick={handleSaveEdit}>
                                Speichern
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className={styles.memoryContent}>
                              <p className={mem.active === false ? styles.inactive : ''}>
                                {mem.content}
                              </p>
                            </div>
                            <div className={styles.memoryActions}>
                              <button
                                className={styles.iconBtn}
                                onClick={() => handleToggle(mem.id)}
                                title={mem.active !== false ? 'Deaktivieren' : 'Aktivieren'}
                              >
                                {mem.active !== false ? '👁️' : '👁️‍🗨️'}
                              </button>
                              <button className={styles.iconBtn} onClick={() => handleStartEdit(mem)} title="Bearbeiten">
                                ✏️
                              </button>
                              <button className={styles.iconBtn} onClick={() => handleDelete(mem.id)} title="Löschen">
                                🗑️
                              </button>
                            </div>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
      </OverlayFooter>
    </Overlay>
  );
}
