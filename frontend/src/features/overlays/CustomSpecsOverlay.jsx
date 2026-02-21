// ── CustomSpecsOverlay ──
// 5 category tabs with forms for custom persona specs

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { GearIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import FormGroup from '../../components/FormGroup/FormGroup';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getCustomSpecs, createCustomSpec, deleteCustomSpec, autofillCustomSpec } from '../../services/customSpecsApi';
import styles from './Overlays.module.css';

const CATEGORIES = [
  { key: 'persona-type', label: '👤 Persona Typ', icon: '👤' },
  { key: 'core-trait', label: '🧠 Core Trait', icon: '🧠' },
  { key: 'knowledge', label: '📚 Wissen', icon: '📚' },
  { key: 'scenario', label: '🌍 Szenario', icon: '🌍' },
  { key: 'expression-style', label: '✍️ Schreibstil', icon: '✍️' },
];

const INITIAL_FORMS = {
  'persona-type': { name: '', description: '' },
  'core-trait': { name: '', description: '', behavior1: '', behavior2: '', behavior3: '' },
  'knowledge': { name: '', description: '' },
  'scenario': { key: '', name: '', description: '', setting1: '', setting2: '', setting3: '', setting4: '' },
  'expression-style': { key: '', name: '', description: '', example: '', char1: '', char2: '', char3: '', char4: '' },
};

export default function CustomSpecsOverlay({ open, onClose }) {
  const [activeTab, setActiveTab] = useState('persona-type');
  const [specs, setSpecs] = useState({});
  const [forms, setForms] = useState({ ...INITIAL_FORMS });
  const [loading, setLoading] = useState(true);
  const [filling, setFilling] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCustomSpecs();
      setSpecs(data.specs || data || {});
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const updateForm = (cat, field, value) => {
    setForms((prev) => ({
      ...prev,
      [cat]: { ...prev[cat], [field]: value },
    }));
  };

  const resetForm = (cat) => {
    setForms((prev) => ({ ...prev, [cat]: { ...INITIAL_FORMS[cat] } }));
  };

  const handleCreate = async () => {
    const form = forms[activeTab];
    let body;

    switch (activeTab) {
      case 'persona-type':
        body = { key: form.name, description: form.description };
        break;
      case 'core-trait':
        body = { key: form.name, description: form.description, behaviors: [form.behavior1, form.behavior2, form.behavior3] };
        break;
      case 'knowledge':
        body = { key: form.name, description: form.description };
        break;
      case 'scenario':
        body = { key: form.key, name: form.name, description: form.description, setting: [form.setting1, form.setting2, form.setting3, form.setting4] };
        break;
      case 'expression-style':
        body = { key: form.key, name: form.name, description: form.description, example: form.example, characteristics: [form.char1, form.char2, form.char3, form.char4].filter(Boolean) };
        break;
    }

    try {
      await createCustomSpec(activeTab, body);
      resetForm(activeTab);
      refresh();
    } catch (err) {
      console.error('Create spec failed:', err);
    }
  };

  const handleDelete = async (key) => {
    try {
      await deleteCustomSpec(activeTab, key);
      refresh();
    } catch {
      // silent
    }
  };

  const handleAutofill = async () => {
    const form = forms[activeTab];
    const input = form.name || form.key || '';
    if (!input) return;

    setFilling(true);
    try {
      const data = await autofillCustomSpec(activeTab, { type: activeTab, input });
      if (data) {
        const updated = { ...form };
        if (data.description) updated.description = data.description;
        if (data.behaviors) {
          updated.behavior1 = data.behaviors[0] || '';
          updated.behavior2 = data.behaviors[1] || '';
          updated.behavior3 = data.behaviors[2] || '';
        }
        if (data.name) updated.name = data.name;
        if (data.setting) {
          updated.setting1 = data.setting[0] || '';
          updated.setting2 = data.setting[1] || '';
          updated.setting3 = data.setting[2] || '';
          updated.setting4 = data.setting[3] || '';
        }
        if (data.example) updated.example = data.example;
        if (data.characteristics) {
          updated.char1 = data.characteristics[0] || '';
          updated.char2 = data.characteristics[1] || '';
          updated.char3 = data.characteristics[2] || '';
          updated.char4 = data.characteristics[3] || '';
        }
        setForms((prev) => ({ ...prev, [activeTab]: updated }));
      }
    } catch {
      // silent
    } finally {
      setFilling(false);
    }
  };

  const currentList = specs[activeTab] || [];
  const form = forms[activeTab];

  const renderForm = () => {
    switch (activeTab) {
      case 'persona-type':
      case 'knowledge':
        return (
          <>
            <FormGroup label="Name" charCount={form.name?.length} maxLength={activeTab === 'knowledge' ? 30 : 40}>
              <input className={styles.textInput} value={form.name} onChange={(e) => updateForm(activeTab, 'name', e.target.value)} maxLength={activeTab === 'knowledge' ? 30 : 40} placeholder="Name eingeben" />
            </FormGroup>
            <FormGroup label="Beschreibung" charCount={form.description?.length} maxLength={120}>
              <div className={styles.inputRow}>
                <input className={styles.textInput} value={form.description} onChange={(e) => updateForm(activeTab, 'description', e.target.value)} maxLength={120} placeholder="Beschreibung" />
                <button className={styles.aiBtn} onClick={handleAutofill} disabled={filling || !form.name} title="KI Auto-Fill">✨</button>
              </div>
            </FormGroup>
          </>
        );

      case 'core-trait':
        return (
          <>
            <FormGroup label="Name" charCount={form.name?.length} maxLength={30}>
              <input className={styles.textInput} value={form.name} onChange={(e) => updateForm(activeTab, 'name', e.target.value)} maxLength={30} placeholder="Trait Name" />
            </FormGroup>
            <FormGroup label="Beschreibung">
              <div className={styles.inputRow}>
                <input className={styles.textInput} value={form.description} onChange={(e) => updateForm(activeTab, 'description', e.target.value)} placeholder="Beschreibung" />
                <button className={styles.aiBtn} onClick={handleAutofill} disabled={filling || !form.name} title="KI Auto-Fill">✨</button>
              </div>
            </FormGroup>
            <FormGroup label="Verhalten 1"><input className={styles.textInput} value={form.behavior1} onChange={(e) => updateForm(activeTab, 'behavior1', e.target.value)} placeholder="Verhaltensweise 1" /></FormGroup>
            <FormGroup label="Verhalten 2"><input className={styles.textInput} value={form.behavior2} onChange={(e) => updateForm(activeTab, 'behavior2', e.target.value)} placeholder="Verhaltensweise 2" /></FormGroup>
            <FormGroup label="Verhalten 3"><input className={styles.textInput} value={form.behavior3} onChange={(e) => updateForm(activeTab, 'behavior3', e.target.value)} placeholder="Verhaltensweise 3" /></FormGroup>
          </>
        );

      case 'scenario':
        return (
          <>
            <FormGroup label="Key" charCount={form.key?.length} maxLength={30}>
              <input className={styles.textInput} value={form.key} onChange={(e) => updateForm(activeTab, 'key', e.target.value)} maxLength={30} placeholder="Eindeutiger Key" />
            </FormGroup>
            <FormGroup label="Anzeigename">
              <input className={styles.textInput} value={form.name} onChange={(e) => updateForm(activeTab, 'name', e.target.value)} placeholder="Anzeigename" />
            </FormGroup>
            <FormGroup label="Beschreibung">
              <div className={styles.inputRow}>
                <input className={styles.textInput} value={form.description} onChange={(e) => updateForm(activeTab, 'description', e.target.value)} placeholder="Beschreibung" />
                <button className={styles.aiBtn} onClick={handleAutofill} disabled={filling || !form.key} title="KI Auto-Fill">✨</button>
              </div>
            </FormGroup>
            {[1, 2, 3, 4].map((n) => (
              <FormGroup key={n} label={`Setting ${n}`}>
                <input className={styles.textInput} value={form[`setting${n}`]} onChange={(e) => updateForm(activeTab, `setting${n}`, e.target.value)} placeholder={`Setting ${n}`} />
              </FormGroup>
            ))}
          </>
        );

      case 'expression-style':
        return (
          <>
            <FormGroup label="Key" charCount={form.key?.length} maxLength={30}>
              <input className={styles.textInput} value={form.key} onChange={(e) => updateForm(activeTab, 'key', e.target.value)} maxLength={30} placeholder="Eindeutiger Key" />
            </FormGroup>
            <FormGroup label="Anzeigename">
              <input className={styles.textInput} value={form.name} onChange={(e) => updateForm(activeTab, 'name', e.target.value)} placeholder="Anzeigename" />
            </FormGroup>
            <FormGroup label="Beschreibung">
              <div className={styles.inputRow}>
                <input className={styles.textInput} value={form.description} onChange={(e) => updateForm(activeTab, 'description', e.target.value)} placeholder="Beschreibung" />
                <button className={styles.aiBtn} onClick={handleAutofill} disabled={filling || !form.key} title="KI Auto-Fill">✨</button>
              </div>
            </FormGroup>
            <FormGroup label="Beispiel-Begrüßung">
              <input className={styles.textInput} value={form.example} onChange={(e) => updateForm(activeTab, 'example', e.target.value)} placeholder="Beispiel" />
            </FormGroup>
            {[1, 2, 3, 4].map((n) => (
              <FormGroup key={n} label={`Merkmal ${n}${n === 4 ? ' (optional)' : ''}`}>
                <input className={styles.textInput} value={form[`char${n}`]} onChange={(e) => updateForm(activeTab, `char${n}`, e.target.value)} placeholder={`Merkmal ${n}`} />
              </FormGroup>
            ))}
          </>
        );
    }
  };

  return (
    <Overlay open={open} onClose={onClose} width="600px">
      <OverlayHeader title="Custom Specs" icon={<GearIcon size={20} />} onClose={onClose} />
      <OverlayBody>
        {/* Category Tabs */}
        <div className={styles.tabBar}>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.key}
              className={`${styles.tab} ${activeTab === cat.key ? styles.activeTab : ''}`}
              onClick={() => setActiveTab(cat.key)}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Form */}
        <div className={styles.specForm}>
          {renderForm()}
          <Button variant="primary" onClick={handleCreate} disabled={filling}>
            Erstellen
          </Button>
        </div>

        {/* Existing list */}
        <div className={styles.specList}>
          <h4 className={styles.sectionTitle}>Vorhandene Einträge</h4>
          {loading ? (
            <Spinner />
          ) : currentList.length === 0 ? (
            <p className={styles.emptyText}>Keine Einträge vorhanden.</p>
          ) : (
            <ul className={styles.ipListVertical}>
              {currentList.map((item, i) => (
                <li key={item.key || i} className={styles.specItem}>
                  <div>
                    <strong>{item.key || item.name}</strong>
                    {item.description && <p className={styles.hint}>{item.description}</p>}
                  </div>
                  <button className={styles.removeBtn} onClick={() => handleDelete(item.key)} title="Löschen">✕</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </OverlayBody>
    </Overlay>
  );
}
