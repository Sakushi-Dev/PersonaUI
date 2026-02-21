// ── CustomSpecsOverlay ──
// 5 category tabs with expandable forms for custom persona specs
// Pattern: ifaceSection / ifaceCard (like InterfaceSettingsOverlay)

import { useState, useEffect } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { GearIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { createCustomSpec, autofillCustomSpec } from '../../services/customSpecsApi';
import styles from './Overlays.module.css';

// ── Categories (no emojis) ──
const CATEGORIES = [
  { key: 'persona-type', label: 'Persona Typ' },
  { key: 'core-trait', label: 'Core Trait' },
  { key: 'knowledge', label: 'Wissen' },
  { key: 'scenario', label: 'Szenario' },
  { key: 'expression-style', label: 'Schreibstil' },
];

// ── Helpers ──
const toKey = (name) => (name || '').trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '').slice(0, 30);

// Map frontend tab keys to backend spec_type values
const toSpecType = (tab) => tab.replace(/-/g, '_');

// Initial form state per category
const makeInitialForm = (cat) => {
  switch (cat) {
    case 'persona-type':
    case 'knowledge':
      return { name: '', description: '' };
    case 'core-trait':
      return { name: '', description: '', items: [''] };
    case 'scenario':
      return { name: '', description: '', items: [''] };
    case 'expression-style':
      return { name: '', description: '', example: '', items: [''] };
    default:
      return { name: '', description: '' };
  }
};

// Which categories have expandable items
const HAS_ITEMS = { 'core-trait': true, scenario: true, 'expression-style': true };
const ITEM_LABEL = {
  'core-trait': 'Verhaltensweise',
  scenario: 'Setting',
  'expression-style': 'Merkmal',
};
const ITEM_MAX = 6;

export default function CustomSpecsOverlay({ open, onClose, onOpenList }) {
  const [activeTab, setActiveTab] = useState('persona-type');
  const [forms, setForms] = useState(() =>
    Object.fromEntries(CATEGORIES.map((c) => [c.key, makeInitialForm(c.key)]))
  );
  const [filling, setFilling] = useState(false);

  useEffect(() => {
    if (open) {
      setActiveTab('persona-type');
      setForms(Object.fromEntries(CATEGORIES.map((c) => [c.key, makeInitialForm(c.key)])));
    }
  }, [open]);

  // ── Form Helpers ──
  const form = forms[activeTab] || {};

  const updateField = (field, value) => {
    setForms((prev) => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], [field]: value },
    }));
  };

  const updateItem = (index, value) => {
    setForms((prev) => {
      const items = [...(prev[activeTab].items || [])];
      items[index] = value;
      return { ...prev, [activeTab]: { ...prev[activeTab], items } };
    });
  };

  const addItem = () => {
    setForms((prev) => {
      const items = [...(prev[activeTab].items || [])];
      if (items.length >= ITEM_MAX) return prev;
      return { ...prev, [activeTab]: { ...prev[activeTab], items: [...items, ''] } };
    });
  };

  const removeItem = (index) => {
    setForms((prev) => {
      const items = [...(prev[activeTab].items || [])];
      if (items.length <= 1) return prev;
      items.splice(index, 1);
      return { ...prev, [activeTab]: { ...prev[activeTab], items } };
    });
  };

  const resetForm = () => {
    setForms((prev) => ({ ...prev, [activeTab]: makeInitialForm(activeTab) }));
  };

  // ── Auto-Fill ──
  const handleAutofill = async () => {
    if (!form.name) return;
    setFilling(true);
    try {
      const itemCount = (form.items || []).length;
      const resp = await autofillCustomSpec(activeTab, {
        type: toSpecType(activeTab),
        input: form.name,
        item_count: itemCount,
      });
      // API returns { result: ... , tokens: ... }
      const data = resp?.result ?? resp;
      if (!data) return;

      const updated = { ...form };

      // For simple types (persona-type, knowledge) result is a string (description)
      if (typeof data === 'string') {
        updated.description = data;
      } else {
        // Structured result for traits, scenarios, expression styles
        if (data.description) updated.description = data.description;
        if (data.name) updated.name = data.name;
        if (data.example) updated.example = data.example;

        // Map array responses into items (only fill as many slots as exist)
        const arrayData = data.behaviors || data.setting || data.characteristics;
        if (arrayData && updated.items) {
          const newItems = [...updated.items];
          for (let i = 0; i < newItems.length && i < arrayData.length; i++) {
            if (arrayData[i]) newItems[i] = arrayData[i];
          }
          updated.items = newItems;
        }
      }

      setForms((prev) => ({ ...prev, [activeTab]: updated }));
    } catch {
      // silent
    } finally {
      setFilling(false);
    }
  };

  // ── Create ──
  const handleCreate = async () => {
    const key = toKey(form.name);
    if (!key) return;

    let body;
    const items = (form.items || []).filter(Boolean);

    switch (activeTab) {
      case 'persona-type':
      case 'knowledge':
        body = { key, description: form.description };
        break;
      case 'core-trait':
        body = { key, description: form.description, behaviors: items };
        break;
      case 'scenario':
        body = { key, name: form.name, description: form.description, setting: items };
        break;
      case 'expression-style':
        body = { key, name: form.name, description: form.description, example: form.example, characteristics: items };
        break;
    }

    try {
      await createCustomSpec(activeTab, body);
      resetForm();
    } catch (err) {
      console.error('Create spec failed:', err);
    }
  };

  // ── Tab Change ──
  const handleTabChange = (key) => {
    setActiveTab(key);
    setFilling(false);
  };

  const hasItems = HAS_ITEMS[activeTab];
  const itemLabel = ITEM_LABEL[activeTab] || 'Eintrag';
  const derivedKey = toKey(form.name);

  return (
    <Overlay open={open} onClose={onClose} width="600px">
      <OverlayHeader title="Custom Specs" icon={<GearIcon size={20} />} onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Kategorie ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Kategorie</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.cortexTabBar}>
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.key}
                  type="button"
                  className={`${styles.cortexTab} ${activeTab === cat.key ? styles.cortexTabActive : ''}`}
                  onClick={() => handleTabChange(cat.key)}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ═══ Section: Neuer Eintrag ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Neuer Eintrag</h3>
          <div className={styles.ifaceCard}>

            {/* Name */}
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Name</span>
              <input
                className={styles.textInput}
                value={form.name}
                onChange={(e) => updateField('name', e.target.value)}
                maxLength={40}
                placeholder="Name eingeben"
                disabled={filling}
              />
              {derivedKey && (
                <span className={styles.csKeyPreview}>
                  Key: {derivedKey}
                </span>
              )}
            </div>

            <div className={styles.ifaceDivider} />

            {/* Description (expanded textarea with autofill overlay) */}
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Beschreibung</span>
              <div className={styles.backgroundTextareaWrapper}>
                <textarea
                  className={styles.textarea}
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  rows={3}
                  placeholder="Beschreibung eingeben..."
                  disabled={filling}
                />
                {filling && (
                  <div className={styles.autofillOverlay}>
                    <Spinner />
                    <span className={styles.autofillOverlayText}>Generiere...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Example (expression-style only) */}
            {activeTab === 'expression-style' && (
              <>
                <div className={styles.ifaceDivider} />
                <div className={styles.ifaceFieldGroup}>
                  <span className={styles.ifaceFieldLabel}>Beispiel</span>
                  <span className={styles.ifaceFieldHint}>Ein typischer Satz in diesem Schreibstil</span>
                  <textarea
                    className={styles.textarea}
                    value={form.example}
                    onChange={(e) => updateField('example', e.target.value)}
                    rows={2}
                    placeholder="Beispiel-Text eingeben..."
                    disabled={filling}
                  />
                </div>
              </>
            )}

            {/* Expandable Items (core-trait / scenario / expression-style) */}
            {hasItems && (
              <>
                <div className={styles.ifaceDivider} />
                <div className={styles.ifaceFieldGroup}>
                  <div className={styles.csItemsHeader}>
                    <span className={styles.ifaceFieldLabel}>
                      {itemLabel === 'Verhaltensweise' ? 'Verhaltensweisen' : itemLabel === 'Setting' ? 'Settings' : 'Merkmale'}
                    </span>
                    <span className={styles.ifaceFieldHint} style={{ margin: 0 }}>
                      {(form.items || []).length} / {ITEM_MAX}
                    </span>
                  </div>
                  <span className={styles.ifaceFieldHint}>
                    Nur so viele hinzufuegen, wie Auto-Fill befuellen soll
                  </span>

                  <div className={styles.csItemsList}>
                    {(form.items || []).map((item, idx) => (
                      <div key={idx} className={styles.csItemRow}>
                        <textarea
                          className={styles.textarea}
                          value={item}
                          onChange={(e) => updateItem(idx, e.target.value)}
                          rows={2}
                          placeholder={`${itemLabel} ${idx + 1}`}
                          disabled={filling}
                        />
                        {(form.items || []).length > 1 && (
                          <button
                            type="button"
                            className={styles.csRemoveItemBtn}
                            onClick={() => removeItem(idx)}
                            title="Entfernen"
                            disabled={filling}
                          >
                            &minus;
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  {(form.items || []).length < ITEM_MAX && (
                    <button
                      type="button"
                      className={styles.csAddItemBtn}
                      onClick={addItem}
                      disabled={filling}
                    >
                      + {itemLabel} hinzufuegen
                    </button>
                  )}
                </div>
              </>
            )}

            <div className={styles.ifaceDivider} />

            {/* Actions */}
            <div className={styles.csFormActions}>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleAutofill}
                disabled={filling || !form.name}
              >
                {filling ? 'Generiert...' : 'Auto-Fill'}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleCreate}
                disabled={filling || !form.name}
              >
                Erstellen
              </Button>
            </div>
          </div>
        </div>

        {/* ═══ Link to library ═══ */}
        {onOpenList && (
          <div className={styles.cslLinkRow}>
            <button type="button" className={styles.cslLinkBtn} onClick={onOpenList}>
              Vorhandene Specs anzeigen
            </button>
          </div>
        )}

      </OverlayBody>
    </Overlay>
  );
}
