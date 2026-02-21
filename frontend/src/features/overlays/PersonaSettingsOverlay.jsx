// ── PersonaSettingsOverlay ──
// Two-view: persona list (contact-list style) → persona creator/editor (config sections)
// Follows legacy HTML structure from _overlay_persona_settings.html

import { useState, useEffect, useCallback } from 'react';
import { useSession } from '../../hooks/useSession';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { PersonaIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import Avatar from '../../components/Avatar/Avatar';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import Toggle from '../../components/Toggle/Toggle';
import {
  getPersonas,
  createPersona,
  updatePersona,
  deletePersona,
  getAvailableOptions,
  backgroundAutofill,
} from '../../services/personaApi';
import styles from './Overlays.module.css';

export default function PersonaSettingsOverlay({ open, onClose, onOpenAvatarEditor, onOpenCustomSpecs, avatarCallbackRef }) {
  const { loadPersonas: refreshSidebarPersonas } = useSession();

  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [personas, setPersonas] = useState([]);
  const [options, setOptions] = useState({});       // options.persona_types, .core_traits, etc.
  const [details, setDetails] = useState({});       // option label details
  const [customKeys, setCustomKeys] = useState({}); // custom spec highlighting
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);

  // Editor state
  const [name, setName] = useState('');
  const [age, setAge] = useState(18);
  const [gender, setGender] = useState('divers');
  const [personaType, setPersonaType] = useState('KI');
  const [scenarios, setScenarios] = useState([]);
  const [coreTraits, setCoreTraits] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [expression, setExpression] = useState('normal');
  const [background, setBackground] = useState('');
  const [startMsgEnabled, setStartMsgEnabled] = useState(false);
  const [startMessage, setStartMessage] = useState('');
  const [avatar, setAvatar] = useState(null);
  const [avatarType, setAvatarType] = useState(null);
  const [saving, setSaving] = useState(false);
  const [filling, setFilling] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [personaData, optData] = await Promise.all([
        getPersonas(),
        getAvailableOptions(),
      ]);
      setPersonas(personaData.personas || []);
      // Extract nested options/details/custom_keys from API response
      setOptions(optData.options || {});
      setDetails(optData.details || {});
      setCustomKeys(optData.custom_keys || {});
    } catch (err) {
      console.error('Persona refresh failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setView('list');
      refresh();
    }
  }, [open, refresh]);

  // Register avatar callback so parent (ChatPage) can pass avatar data from AvatarEditorOverlay
  useEffect(() => {
    if (avatarCallbackRef) {
      avatarCallbackRef.current = (filename, type) => {
        setAvatar(filename);
        setAvatarType(type);
      };
    }
    return () => {
      if (avatarCallbackRef) avatarCallbackRef.current = null;
    };
  }, [avatarCallbackRef]);

  const resetEditor = () => {
    setEditingId(null);
    setName('');
    setAge(18);
    setGender('divers');
    setPersonaType('KI');
    setScenarios([]);
    setCoreTraits([]);
    setKnowledge([]);
    setExpression('normal');
    setBackground('');
    setStartMsgEnabled(false);
    setStartMessage('');
    setAvatar(null);
    setAvatarType(null);
  };

  const openEditor = (persona = null) => {
    if (persona) {
      setEditingId(persona.id);
      setName(persona.name || '');
      setAge(persona.age || 18);
      setGender(persona.gender || 'weiblich');
      setPersonaType(persona.persona || 'KI');
      setScenarios(persona.scenarios || []);
      setCoreTraits(persona.core_traits || []);
      setKnowledge(persona.knowledge || []);
      setExpression(persona.expression || 'normal');
      setBackground(persona.background || '');
      setStartMsgEnabled(persona.start_msg_enabled || false);
      setStartMessage(persona.start_msg || '');
      setAvatar(persona.avatar || null);
      setAvatarType(persona.avatar_type || null);
    } else {
      resetEditor();
    }
    setView('editor');
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);

    const data = {
      name: name.trim(),
      age,
      gender,
      persona: personaType,
      core_traits: coreTraits,
      knowledge,
      expression,
      background,
      scenarios,
      start_msg_enabled: startMsgEnabled,
      start_msg: startMsgEnabled ? startMessage : '',
      avatar,
      avatar_type: avatarType,
      tools_enabled: true,
      system_access: 'soul',
      persona_type: 'sub',
    };

    try {
      if (editingId) {
        await updatePersona(editingId, data);
      } else {
        await createPersona(data);
      }
      setView('list');
      await refresh();
      // Refresh sidebar persona list
      await refreshSidebarPersonas();
    } catch (err) {
      console.error('Persona save failed:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Möchtest du diese Persona wirklich löschen?')) return;
    try {
      await deletePersona(id);
      await refresh();
      // Refresh sidebar persona list
      await refreshSidebarPersonas();
    } catch (err) {
      console.error('Persona delete failed:', err);
    }
  };

  const handleAutofill = async () => {
    setFilling(true);
    try {
      const data = await backgroundAutofill({
        name,
        age,
        gender,
        persona: personaType,
        core_traits: coreTraits,
        knowledge,
        expression,
        scenarios,
        background_hint: background.trim(),
      });
      if (data.background) setBackground(data.background);
    } catch (err) {
      console.error('Autofill failed:', err);
    } finally {
      setFilling(false);
    }
  };

  // Get option arrays from loaded options (options now correctly contains persona_types, core_traits, etc.)
  const typeOptions = (options.persona_types || []).map((t) =>
    typeof t === 'string' ? { key: t, label: t } : { key: t.key || t, label: t.name || t.key || t }
  );
  const traitOptions = (options.core_traits || []).map((t) => typeof t === 'string' ? t : t.key || t);
  const knowledgeOptions = (options.knowledge || []).map((k) => typeof k === 'string' ? k : k.key || k);
  const expressionOptions = (options.expression_styles || []).map((e) => {
    if (typeof e === 'string') {
      const detail = details?.expression_styles?.[e];
      return { key: e, label: detail?.name || e };
    }
    return { key: e.key || e, label: e.name || e.key || e };
  });
  const scenarioOptions = (options.scenarios || []).map((s) => {
    if (typeof s === 'string') {
      const detail = details?.scenarios?.[s];
      return { key: s, label: detail?.name || s };
    }
    return { key: s.key || s, label: s.name || s.key || s };
  });

  // Toggle helpers for tag-based selectors
  const toggleTag = (list, setList, tag) => {
    setList((prev) => prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]);
  };

  const showScenario = personaType !== 'KI' && scenarioOptions.length > 0;

  // ── List View ──────────────────────────────────────────
  if (view === 'list') {
    return (
      <Overlay open={open} onClose={onClose} width="1200px">
        <OverlayHeader title="Persona Einstellungen" icon={<PersonaIcon size={20} />} onClose={onClose} />
        <OverlayBody>
          {loading ? (
            <Spinner />
          ) : (
            <>
              {/* List Header */}
              <div className={styles.personaListHeader}>
                <h3 className={styles.personaListTitle}>Meine Personas</h3>
                <button className={styles.specsBtn} onClick={() => onOpenCustomSpecs?.()}>
                  <span className={styles.specsBtnIcon}>✦</span> Custom Specs
                </button>
              </div>

              {/* Contact List */}
              <div className={styles.personaContactList}>
                {personas.map((p) => (
                  <div
                    key={p.id}
                    className={styles.personaContactItem}
                  >
                    <Avatar src={p.avatar} type={p.avatar_type} name={p.name} size={46} />
                    <div className={styles.personaContactInfo}>
                      <span className={styles.personaContactName}>{p.name || 'Unbenannt'}</span>
                      <span className={styles.personaContactType}>{p.persona || 'KI'}</span>
                    </div>

                    {/* Badges */}
                    <div className={styles.personaContactBadges}>
                      {p.is_active && (
                        <span className={`${styles.personaBadge} ${styles.activeBadge}`}>Aktiv</span>
                      )}
                      {p.is_default && (
                        <span className={`${styles.personaBadge} ${styles.defaultBadge}`}>Standard</span>
                      )}
                    </div>

                    {/* Hover Actions */}
                    {!p.is_default && (
                      <div className={styles.personaContactActions}>
                        <button
                          className={styles.personaEditBtn}
                          onClick={(e) => { e.stopPropagation(); openEditor(p); }}
                          title="Bearbeiten"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button
                          className={styles.personaDeleteBtn}
                          onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                          title="Löschen"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Add-Button Row */}
              <div
                className={styles.personaAddRow}
                onClick={() => openEditor()}
                title="Neue Persona erstellen"
              >
                <div className={styles.personaAddCircle}>+</div>
                <span className={styles.personaAddLabel}>Neue Persona erstellen</span>
              </div>
            </>
          )}
        </OverlayBody>
      </Overlay>
    );
  }

  // ── Editor / Creator View ──────────────────────────────
  return (
    <Overlay open={open} onClose={onClose} width="1200px">
      <OverlayHeader
        title={editingId ? `${name || 'Persona'} bearbeiten` : 'Persona Creator'}
        icon={<PersonaIcon size={20} />}
        onClose={onClose}
      />
      <OverlayBody>
        {/* Creator Header */}
        <div className={styles.personaCreatorHeader}>
          <button className={styles.btnBack} onClick={() => setView('list')}>
            ← Zurück
          </button>
          <h3 className={styles.personaCreatorTitle}>
            {editingId ? `${name || 'Persona'} bearbeiten` : 'Persona Creator'}
          </h3>
        </div>

        {/* Scrollable Config Sections */}
        <div className={styles.personaCreatorLayout}>

          {/* ── Avatar Section ── */}
          <div className={styles.configSection}>
            <h3 className={styles.configSectionTitle}>Avatar</h3>
            <div className={styles.configDescription}>Wähle ein Bild für deine Persona:</div>
            <div className={styles.creatorAvatarArea}>
              <div
                className={styles.creatorAvatarPreview}
                onClick={() => onOpenAvatarEditor?.('persona')}
              >
                {avatar ? (
                  <Avatar src={avatar} type={avatarType} name={name || '?'} size={76} />
                ) : (
                  <span className={styles.avatarPlaceholderText}>Kein Avatar</span>
                )}
              </div>
              <Button variant="secondary" onClick={() => onOpenAvatarEditor?.('persona')}>
                Avatar auswählen
              </Button>
            </div>
          </div>

          {/* ── Persona Info Section ── */}
          <div className={styles.configSection}>
            <h3 className={styles.configSectionTitle}>Persona Info</h3>
            <div className={styles.personaInfoGrid}>
              {/* Name */}
              <div className={styles.personaInfoField}>
                <label className={styles.configDescription} style={{ marginBottom: 0 }}>Name:</label>
                <input
                  className={styles.textInput}
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="z.B. Ayame"
                  disabled={!!editingId}
                  style={editingId ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}
                />
              </div>

              {/* Age */}
              <div className={styles.personaInfoField}>
                <label className={styles.configDescription} style={{ marginBottom: 0 }}>
                  Alter: <span>{age}</span>
                </label>
                <input
                  type="range"
                  min={18}
                  max={99}
                  value={age}
                  onChange={(e) => setAge(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Gender - Full Width */}
              <div className={`${styles.personaInfoField} ${styles.personaInfoFieldFull}`}>
                <label className={styles.configDescription} style={{ marginBottom: 0 }}>Geschlecht:</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['männlich', 'weiblich', 'divers'].map((g) => (
                    <label
                      key={g}
                      className={styles.tagButton + (gender === g ? ` ${styles.tagButtonActive}` : '')}
                      style={{ flex: 1, textAlign: 'center', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                    >
                      <input
                        type="radio"
                        name="persona-gender"
                        value={g}
                        checked={gender === g}
                        onChange={() => setGender(g)}
                        style={{ display: 'none' }}
                      />
                      {g.charAt(0).toUpperCase() + g.slice(1)}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* ── Persona Type Section ── */}
          {typeOptions.length > 0 && (
            <div className={styles.configSection}>
              <h3 className={styles.configSectionTitle}>Persona</h3>
              <div className={styles.configDescription}>Art der Persona:</div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {typeOptions.map((t) => (
                  <label
                    key={t.key}
                    className={styles.tagButton + (personaType === t.key ? ` ${styles.tagButtonActive}` : '')}
                    style={{ flex: '1 1 120px', textAlign: 'center', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '12px 16px' }}
                  >
                    <input
                      type="radio"
                      name="persona-type"
                      value={t.key}
                      checked={personaType === t.key}
                      onChange={() => {
                        setPersonaType(t.key);
                        // Clear scenarios when switching to KI (matches legacy behavior)
                        if (t.key === 'KI') setScenarios([]);
                      }}
                      style={{ display: 'none' }}
                    />
                    {t.label}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* ── Scenario Section (slide in/out) ── */}
          <div className={`${styles.configSection} ${styles.scenarioSlide} ${showScenario ? styles.scenarioVisible : ''}`}>
            <h3 className={styles.configSectionTitle}>Szenario</h3>
            <div className={styles.configDescription}>Wähle ein oder mehrere Settings (kombinierbar):</div>
            <div className={styles.tagsAvailable}>
              {scenarioOptions.map((opt) => (
                <button
                  key={opt.key}
                  className={styles.tagButton + (scenarios.includes(opt.key) ? ` ${styles.tagButtonActive}` : '')}
                  onClick={() => toggleTag(scenarios, setScenarios, opt.key)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div className={styles.tagsActiveContainer}>
              <h4 className={styles.tagsActiveTitle}>Aktiv ({scenarios.length}):</h4>
              <div className={styles.tagsActive}>
                {scenarios.map((key) => (
                  <button
                    key={key}
                    className={`${styles.tagButton} ${styles.tagButtonActive}`}
                    onClick={() => toggleTag(scenarios, setScenarios, key)}
                  >
                    {scenarioOptions.find((o) => o.key === key)?.label || key}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* ── Core Traits Section ── */}
          {traitOptions.length > 0 && (
            <div className={styles.configSection}>
              <h3 className={styles.configSectionTitle}>Core Traits</h3>
              <div className={styles.configDescription}>Wähle Persönlichkeitsmerkmale:</div>
              <div className={styles.tagsAvailable}>
                {traitOptions.map((tag) => (
                  <button
                    key={tag}
                    className={styles.tagButton + (coreTraits.includes(tag) ? ` ${styles.tagButtonActive}` : '')}
                    onClick={() => toggleTag(coreTraits, setCoreTraits, tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
              <div className={styles.tagsActiveContainer}>
                <h4 className={styles.tagsActiveTitle}>Aktiv ({coreTraits.length}):</h4>
                <div className={styles.tagsActive}>
                  {coreTraits.map((tag) => (
                    <button
                      key={tag}
                      className={`${styles.tagButton} ${styles.tagButtonActive}`}
                      onClick={() => toggleTag(coreTraits, setCoreTraits, tag)}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Knowledge Section ── */}
          {knowledgeOptions.length > 0 && (
            <div className={styles.configSection}>
              <h3 className={styles.configSectionTitle}>Knowledge</h3>
              <div className={styles.configDescription}>Wähle Wissensgebiete:</div>
              <div className={styles.tagsAvailable}>
                {knowledgeOptions.map((tag) => (
                  <button
                    key={tag}
                    className={styles.tagButton + (knowledge.includes(tag) ? ` ${styles.tagButtonActive}` : '')}
                    onClick={() => toggleTag(knowledge, setKnowledge, tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
              <div className={styles.tagsActiveContainer}>
                <h4 className={styles.tagsActiveTitle}>Aktiv ({knowledge.length}):</h4>
                <div className={styles.tagsActive}>
                  {knowledge.map((tag) => (
                    <button
                      key={tag}
                      className={`${styles.tagButton} ${styles.tagButtonActive}`}
                      onClick={() => toggleTag(knowledge, setKnowledge, tag)}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Expression Section ── */}
          {expressionOptions.length > 0 && (
            <div className={styles.configSection}>
              <h3 className={styles.configSectionTitle}>Expression</h3>
              <div className={styles.configDescription}>Wähle einen Schreibstil:</div>
              <div className={styles.tagsAvailable}>
                {expressionOptions.map((opt) => (
                  <button
                    key={opt.key}
                    className={styles.tagButton + (expression === opt.key ? ` ${styles.tagButtonActive}` : '')}
                    onClick={() => setExpression(opt.key)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <div className={styles.tagsActiveContainer}>
                <h4 className={styles.tagsActiveTitle}>Aktiv:</h4>
                <div className={styles.tagsActive}>
                  {expression && (
                    <button
                      className={`${styles.tagButton} ${styles.tagButtonActive}`}
                      onClick={() => setExpression('')}
                    >
                      {expressionOptions.find((o) => o.key === expression)?.label || expression}
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Background Section ── */}
          <div className={styles.configSection}>
            <h3 className={styles.configSectionTitle}>Background</h3>
            <div className={styles.configDescription}>Hintergrundgeschichte der Persona (optional):</div>
            <div className={styles.backgroundInputArea}>
              <textarea
                className={styles.textarea}
                value={background}
                onChange={(e) => setBackground(e.target.value)}
                placeholder="Beschreibe die Hintergrundgeschichte deiner Persona oder nutze Auto-Fill..."
                maxLength={1500}
                rows={4}
              />
              <div className={styles.backgroundFooter}>
                <span className={styles.charCounter}>
                  {background.length} / 1500
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleAutofill}
                  disabled={filling || !name}
                  title="KI generiert eine Hintergrundgeschichte basierend auf den Persona-Einstellungen"
                >
                  ✨ Auto-Fill
                </Button>
              </div>
            </div>
          </div>

          {/* ── First Message Section ── */}
          <div className={styles.configSection}>
            <h3 className={styles.configSectionTitle}>First Message</h3>
            <div className={styles.firstMessageToggle}>
              <Toggle
                label="First Message aktivieren"
                checked={startMsgEnabled}
                onChange={setStartMsgEnabled}
                id="start-msg-toggle"
              />
              <p className={styles.configHint}>
                Die First Message wird in jeder neuen Session als erste Nachricht der Persona gesendet, sodass das Gespräch immer auf dieser Sequenz aufbaut.
              </p>
            </div>
            {startMsgEnabled && (
              <div className={styles.startMsgInputArea}>
                <textarea
                  className={styles.textarea}
                  value={startMessage}
                  onChange={(e) => setStartMessage(e.target.value)}
                  placeholder="z.B. *lächelt freundlich* Hey! Schön dich zu sehen..."
                  maxLength={1000}
                  rows={3}
                />
                <div className={styles.startMsgFooter}>
                  <span className={styles.charCounter}>
                    {startMessage.length} / 1000
                  </span>
                  <span className={styles.configHintInline}>
                    Für nonverbale Formatierung RAW verwenden (z.B. *Aktion*)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Creator Footer */}
        <div className={styles.personaCreatorFooter}>
          <Button variant="secondary" onClick={resetEditor}>Reset</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? 'Speichert...' : 'Persona speichern'}
          </Button>
        </div>
      </OverlayBody>
    </Overlay>
  );
}
