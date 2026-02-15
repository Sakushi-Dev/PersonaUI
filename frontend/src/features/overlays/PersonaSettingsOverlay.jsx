// ── PersonaSettingsOverlay ──
// Two-view: persona list → persona editor/creator

import { useState, useEffect, useCallback } from 'react';
import { useSession } from '../../hooks/useSession';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import ChipSelector from '../../components/ChipSelector/ChipSelector';
import TagSelector from '../../components/TagSelector/TagSelector';
import Slider from '../../components/Slider/Slider';
import Toggle from '../../components/Toggle/Toggle';
import Avatar from '../../components/Avatar/Avatar';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import {
  getPersonas,
  createPersona,
  updatePersona,
  deletePersona,
  activatePersona,
  getAvailableOptions,
  backgroundAutofill,
  restoreDefaultPersona,
} from '../../services/personaApi';
import styles from './Overlays.module.css';

const GENDER_OPTIONS = [
  { value: 'männlich', label: 'Männlich' },
  { value: 'weiblich', label: 'Weiblich' },
  { value: 'divers', label: 'Divers' },
];

export default function PersonaSettingsOverlay({ open, onClose, onOpenAvatarEditor, onOpenCustomSpecs }) {
  const { switchPersona } = useSession();

  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [personas, setPersonas] = useState([]);
  const [options, setOptions] = useState({});
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);

  // Editor state
  const [name, setName] = useState('');
  const [age, setAge] = useState(18);
  const [gender, setGender] = useState('weiblich');
  const [personaType, setPersonaType] = useState('');
  const [scenarios, setScenarios] = useState([]);
  const [coreTraits, setCoreTraits] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [expression, setExpression] = useState('');
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
      setPersonas(personaData.personas || personaData || []);
      setOptions(optData || {});
    } catch {
      // silent
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

  const resetEditor = () => {
    setEditingId(null);
    setName('');
    setAge(18);
    setGender('weiblich');
    setPersonaType('');
    setScenarios([]);
    setCoreTraits([]);
    setKnowledge([]);
    setExpression('');
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
      setPersonaType(persona.persona || '');
      setScenarios(persona.scenarios || []);
      setCoreTraits(persona.core_traits || []);
      setKnowledge(persona.knowledge || []);
      setExpression(persona.expression || '');
      setBackground(persona.background || '');
      setStartMsgEnabled(!!persona.start_message);
      setStartMessage(persona.start_message || '');
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
      start_message: startMsgEnabled ? startMessage : '',
      avatar,
      avatar_type: avatarType,
    };

    try {
      if (editingId) {
        await updatePersona(editingId, data);
      } else {
        await createPersona(data);
      }
      setView('list');
      refresh();
    } catch (err) {
      console.error('Persona save failed:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deletePersona(id);
      refresh();
    } catch {
      // silent
    }
  };

  const handleActivate = async (id) => {
    try {
      await activatePersona(id);
      await switchPersona(id);
      onClose();
    } catch {
      // silent
    }
  };

  const handleRestoreDefault = async () => {
    try {
      await restoreDefaultPersona();
      await switchPersona(null);
      refresh();
    } catch {
      // silent
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
      });
      if (data.background) setBackground(data.background);
    } catch {
      // silent
    } finally {
      setFilling(false);
    }
  };

  // Get option arrays from loaded options
  const typeOptions = (options.persona_types || []).map((t) => ({
    value: typeof t === 'string' ? t : t.key,
    label: typeof t === 'string' ? t : t.name || t.key,
  }));
  const traitOptions = (options.core_traits || []).map((t) => typeof t === 'string' ? t : t.key || t);
  const knowledgeOptions = (options.knowledge || []).map((k) => typeof k === 'string' ? k : k.key || k);
  const expressionOptions = (options.expressions || options.expression_styles || []).map((e) => ({
    value: typeof e === 'string' ? e : e.key,
    label: typeof e === 'string' ? e : e.name || e.key,
  }));
  const scenarioOptions = (options.scenarios || []).map((s) => typeof s === 'string' ? s : s.key || s);

  // ── List View ──
  if (view === 'list') {
    return (
      <Overlay open={open} onClose={onClose} width="560px">
        <OverlayHeader title="Persona Einstellungen" onClose={onClose} />
        <OverlayBody>
          {loading ? (
            <Spinner />
          ) : (
            <>
              <div className={styles.personaGrid}>
                {personas.map((p) => (
                  <div key={p.id} className={styles.personaCard}>
                    <Avatar src={p.avatar} type={p.avatar_type} name={p.name} size={48} />
                    <div className={styles.personaInfo}>
                      <strong>{p.name}</strong>
                      <span className={styles.hint}>{p.persona || 'KI'}</span>
                    </div>
                    <div className={styles.personaActions}>
                      <button className={styles.iconBtn} onClick={() => handleActivate(p.id)} title="Aktivieren">▶</button>
                      <button className={styles.iconBtn} onClick={() => openEditor(p)} title="Bearbeiten">✏️</button>
                      <button className={styles.iconBtn} onClick={() => handleDelete(p.id)} title="Löschen">🗑️</button>
                    </div>
                  </div>
                ))}
              </div>

              <div className={styles.listActions}>
                <Button variant="secondary" onClick={() => onOpenCustomSpecs?.()}>
                  Custom Specs
                </Button>
                <Button variant="secondary" onClick={handleRestoreDefault}>
                  Standard wiederherstellen
                </Button>
                <Button variant="primary" onClick={() => openEditor()}>
                  + Neue Persona erstellen
                </Button>
              </div>
            </>
          )}
        </OverlayBody>
      </Overlay>
    );
  }

  // ── Editor View ──
  return (
    <Overlay open={open} onClose={onClose} width="580px">
      <OverlayHeader
        title={editingId ? `${name || 'Persona'} bearbeiten` : 'Persona Creator'}
        onClose={onClose}
      />
      <OverlayBody>
        <button className={styles.backBtn} onClick={() => setView('list')}>
          ← Zurück zur Liste
        </button>

        {/* Avatar */}
        <div className={styles.profileAvatar}>
          <Avatar
            src={avatar}
            type={avatarType}
            name={name || '?'}
            size={80}
            onClick={() => onOpenAvatarEditor?.('persona')}
            className={styles.clickableAvatar}
          />
          <p className={styles.hint}>Klicken zum Ändern</p>
        </div>

        <FormGroup label="Name">
          <input
            className={styles.textInput}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="z.B. Ayame"
            disabled={!!editingId}
            style={editingId ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}
          />
        </FormGroup>

        <Slider
          label="Alter"
          value={age}
          onChange={(v) => setAge(Math.round(v))}
          min={18}
          max={99}
          step={1}
          displayValue={String(age)}
        />

        <FormGroup label="Geschlecht">
          <ChipSelector
            options={GENDER_OPTIONS}
            value={gender}
            onChange={setGender}
          />
        </FormGroup>

        {typeOptions.length > 0 && (
          <FormGroup label="Persona Typ">
            <ChipSelector
              options={typeOptions}
              value={personaType}
              onChange={setPersonaType}
            />
          </FormGroup>
        )}

        {personaType !== 'KI' && scenarioOptions.length > 0 && (
          <FormGroup label={`Szenario (${scenarios.length})`}>
            <TagSelector
              options={scenarioOptions}
              selected={scenarios}
              onToggle={(tag) => {
                setScenarios((prev) =>
                  prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
                );
              }}
            />
          </FormGroup>
        )}

        {traitOptions.length > 0 && (
          <FormGroup label={`Core Traits (${coreTraits.length})`}>
            <TagSelector
              options={traitOptions}
              selected={coreTraits}
              onToggle={(tag) => {
                setCoreTraits((prev) =>
                  prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
                );
              }}
            />
          </FormGroup>
        )}

        {knowledgeOptions.length > 0 && (
          <FormGroup label={`Wissen (${knowledge.length})`}>
            <TagSelector
              options={knowledgeOptions}
              selected={knowledge}
              onToggle={(tag) => {
                setKnowledge((prev) =>
                  prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
                );
              }}
            />
          </FormGroup>
        )}

        {expressionOptions.length > 0 && (
          <FormGroup label="Ausdruck">
            <ChipSelector
              options={expressionOptions}
              value={expression}
              onChange={setExpression}
            />
          </FormGroup>
        )}

        <FormGroup label="Hintergrund" charCount={background.length} maxLength={1500}>
          <div className={styles.inputRow}>
            <textarea
              className={styles.textarea}
              value={background}
              onChange={(e) => setBackground(e.target.value)}
              maxLength={1500}
              rows={4}
              placeholder="Hintergrundgeschichte..."
            />
          </div>
          <Button variant="ghost" size="sm" onClick={handleAutofill} disabled={filling || !name}>
            ✨ Auto-Fill
          </Button>
        </FormGroup>

        <div className={styles.settingRow}>
          <Toggle
            label={startMsgEnabled ? 'An' : 'Aus'}
            checked={startMsgEnabled}
            onChange={setStartMsgEnabled}
            id="start-msg-toggle"
          />
          <span className={styles.settingLabel}>Erste Nachricht</span>
        </div>

        {startMsgEnabled && (
          <FormGroup label="Erste Nachricht" charCount={startMessage.length} maxLength={1000}>
            <textarea
              className={styles.textarea}
              value={startMessage}
              onChange={(e) => setStartMessage(e.target.value)}
              maxLength={1000}
              rows={3}
              placeholder="Erste Nachricht der Persona..."
            />
          </FormGroup>
        )}
      </OverlayBody>
      <OverlayFooter>
        <Button variant="secondary" onClick={resetEditor}>Zurücksetzen</Button>
        <Button variant="primary" onClick={handleSave} disabled={saving || !name.trim()}>
          {saving ? 'Speichert...' : 'Persona speichern'}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
