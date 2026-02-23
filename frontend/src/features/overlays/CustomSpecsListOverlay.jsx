// ── CustomSpecsListOverlay ──
// Browse, view, edit and delete existing custom persona specs
// Pattern: ifaceSection / ifaceCard (like InterfaceSettingsOverlay)

import { useState, useEffect, useCallback, useMemo } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { GearIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getCustomSpecs, deleteCustomSpec, createCustomSpec } from '../../services/customSpecsApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

// ── Categories with mapping to backend keys ──
const CATEGORY_KEYS = [
  { key: 'persona-type', labelKey: 'personaType', specKey: 'persona_type' },
  { key: 'core-trait', labelKey: 'coreTrait', specKey: 'core_traits_details' },
  { key: 'knowledge', labelKey: 'knowledge', specKey: 'knowledge_areas' },
  { key: 'scenario', labelKey: 'scenario', specKey: 'scenarios' },
  { key: 'expression-style', labelKey: 'expressionStyle', specKey: 'expression_styles' },
];

// Which categories have expandable item arrays
const ITEMS_FIELD_KEYS = {
  'core-trait': { field: 'behaviors', labelKey: 'behaviorPlural' },
  scenario: { field: 'setting', labelKey: 'settingPlural' },
  'expression-style': { field: 'characteristics', labelKey: 'characteristicPlural' },
};

const ITEMS_MAX = 6;

// Ensure a value is a renderable string
function toStr(val) {
  if (!val) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'object') return val.description || '';
  return String(val);
}

// ── Parse backend dict → flat entry array ──
function parseEntries(specData) {
  if (!specData || typeof specData !== 'object') return [];
  return Object.entries(specData).map(([key, val]) => {
    // Simple string value (persona_type, knowledge_areas)
    if (typeof val === 'string') return { key, description: val };

    // Object value — spread fields, ensure description is a string
    const entry = { key, ...val };
    entry.description = toStr(entry.description);
    return entry;
  });
}

export default function CustomSpecsListOverlay({ open, onClose, onOpenCreate }) {
  const { t } = useLanguage();
  const s = t('customSpecsList');

  const categories = useMemo(() =>
    CATEGORY_KEYS.map((c) => ({ ...c, label: s[c.labelKey] })), [s]);

  const [activeTab, setActiveTab] = useState('persona-type');
  const [specs, setSpecs] = useState({});
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState(null);

  // ── Data Loading ──
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCustomSpecs();
      const raw = data.specs || data || {};
      setSpecs(raw.persona_spec || {});
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setActiveTab('persona-type');
      setExpanded(null);
      setEditing(null);
      setEditForm(null);
      refresh();
    }
  }, [open, refresh]);

  // ── Derived ──
  const cat = categories.find((c) => c.key === activeTab);
  const catKey = CATEGORY_KEYS.find((c) => c.key === activeTab);
  const entries = catKey ? parseEntries(specs[catKey.specKey]) : [];
  const itemsFieldKey = ITEMS_FIELD_KEYS[activeTab];
  const itemsInfo = itemsFieldKey ? { field: itemsFieldKey.field, label: s[itemsFieldKey.labelKey] } : null;

  // ── Tab Change ──
  const handleTabChange = (key) => {
    setActiveTab(key);
    setExpanded(null);
    setEditing(null);
    setEditForm(null);
  };

  // ── Expand / Collapse ──
  const toggleExpand = (key) => {
    if (editing) return;
    setExpanded((prev) => (prev === key ? null : key));
  };

  // ── Delete ──
  const handleDelete = async (key) => {
    try {
      await deleteCustomSpec(activeTab, key);
      if (expanded === key) setExpanded(null);
      if (editing === key) { setEditing(null); setEditForm(null); }
      refresh();
    } catch {
      // silent
    }
  };

  // ── Edit: Start ──
  const startEdit = (entry) => {
    setEditing(entry.key);
    setExpanded(entry.key);
    const form = { key: entry.key, description: entry.description || '' };
    if (entry.name) form.name = entry.name;
    if (entry.example !== undefined) form.example = entry.example;
    if (itemsInfo) {
      form.items = [...(entry[itemsInfo.field] || [])];
      if (form.items.length === 0) form.items = [''];
    }
    setEditForm(form);
  };

  // ── Edit: Cancel ──
  const cancelEdit = () => {
    setEditing(null);
    setEditForm(null);
  };

  // ── Edit: Field Updates ──
  const updateEditField = (field, value) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
  };

  const updateEditItem = (idx, value) => {
    setEditForm((prev) => {
      const items = [...(prev.items || [])];
      items[idx] = value;
      return { ...prev, items };
    });
  };

  const addEditItem = () => {
    setEditForm((prev) => {
      const items = [...(prev.items || [])];
      if (items.length >= ITEMS_MAX) return prev;
      return { ...prev, items: [...items, ''] };
    });
  };

  const removeEditItem = (idx) => {
    setEditForm((prev) => {
      const items = [...(prev.items || [])];
      if (items.length <= 1) return prev;
      items.splice(idx, 1);
      return { ...prev, items };
    });
  };

  // ── Edit: Save (delete + re-create) ──
  const saveEdit = async () => {
    if (!editForm) return;
    try {
      await deleteCustomSpec(activeTab, editForm.key);

      let body;
      const items = (editForm.items || []).filter(Boolean);

      switch (activeTab) {
        case 'persona-type':
        case 'knowledge':
          body = { key: editForm.key, description: editForm.description };
          break;
        case 'core-trait':
          body = { key: editForm.key, description: editForm.description, behaviors: items };
          break;
        case 'scenario':
          body = {
            key: editForm.key,
            name: editForm.name || editForm.key,
            description: editForm.description,
            setting: items,
          };
          break;
        case 'expression-style':
          body = {
            key: editForm.key,
            name: editForm.name || editForm.key,
            description: editForm.description,
            example: editForm.example || '',
            characteristics: items,
          };
          break;
      }

      await createCustomSpec(activeTab, body);
      setEditing(null);
      setEditForm(null);
      refresh();
    } catch (err) {
      console.error('Edit save failed:', err);
    }
  };

  // ═══════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════
  return (
    <Overlay open={open} onClose={onClose} width="600px">
      <OverlayHeader title={s.title} icon={<GearIcon size={20} />} onClose={onClose} />
      <OverlayBody>

        {/* ═══ Back ═══ */}
        {onOpenCreate && (
          <button type="button" className={styles.cslBackBtn} onClick={onOpenCreate}>
            {s.back}
          </button>
        )}

        {/* ═══ Section: Kategorie ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.category}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.cortexTabBar}>
              {categories.map((c) => {
                const count = Object.keys(specs[c.specKey] || {}).length;
                return (
                  <button
                    key={c.key}
                    type="button"
                    className={`${styles.cortexTab} ${activeTab === c.key ? styles.cortexTabActive : ''}`}
                    onClick={() => handleTabChange(c.key)}
                  >
                    {c.label}
                    {count > 0 && <span className={styles.cslBadge}>{count}</span>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ═══ Section: Eintraege ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>
            {s.entries}
            <span className={styles.accessBadgeCount}>{entries.length}</span>
          </h3>
          <div className={styles.ifaceCard}>
            {loading ? (
              <div className={styles.centeredContent}><Spinner /></div>
            ) : entries.length === 0 ? (
              <div className={styles.accessEmptyState}>
                <span className={styles.ifaceToggleHint}>{s.noEntries}</span>
                {onOpenCreate && (
                  <Button variant="secondary" size="sm" onClick={onOpenCreate} style={{ marginTop: 8 }}>
                    {s.createNew}
                  </Button>
                )}
              </div>
            ) : (
              <div className={styles.cslEntryList}>
                {entries.map((entry, i) => {
                  const isExpanded = expanded === entry.key;
                  const isEditing = editing === entry.key;

                  return (
                    <div key={entry.key}>
                      {/* ── Entry Header ── */}
                      <div
                        className={`${styles.cslEntryHeader} ${isExpanded ? styles.cslEntryHeaderActive : ''}`}
                        onClick={() => !isEditing && toggleExpand(entry.key)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && !isEditing && toggleExpand(entry.key)}
                      >
                        <div className={styles.cslEntryInfo}>
                          <span className={styles.cslEntryName}>{entry.name || entry.key}</span>
                          {!isExpanded && entry.description && (
                            <span className={styles.cslEntryPreview}>
                              {toStr(entry.description).length > 80
                                ? toStr(entry.description).slice(0, 80) + '...'
                                : toStr(entry.description)}
                            </span>
                          )}
                        </div>
                        <div className={styles.cslEntryActions}>
                          {!isEditing && (
                            <>
                              <button
                                type="button"
                                className={styles.cslBtnEdit}
                                onClick={(e) => { e.stopPropagation(); startEdit(entry); }}
                              >
                                {s.editEntry}
                              </button>
                              <button
                                type="button"
                                className={styles.cslBtnDelete}
                                onClick={(e) => { e.stopPropagation(); handleDelete(entry.key); }}
                              >
                                {s.deleteEntry}
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {/* ── Expanded: View or Edit ── */}
                      {isExpanded && (
                        <div className={styles.cslEntryBody}>
                          {isEditing && editForm ? (
                            /* ── Edit Mode ── */
                            <>
                              {/* Name (scenario, expression-style) */}
                              {(activeTab === 'scenario' || activeTab === 'expression-style') && (
                                <div className={styles.ifaceFieldGroup}>
                                  <span className={styles.ifaceFieldLabel}>{s.name}</span>
                                  <input
                                    className={styles.textInput}
                                    value={editForm.name || ''}
                                    onChange={(e) => updateEditField('name', e.target.value)}
                                    maxLength={40}
                                  />
                                </div>
                              )}

                              {/* Description */}
                              <div className={styles.ifaceFieldGroup}>
                                <span className={styles.ifaceFieldLabel}>{s.description}</span>
                                <textarea
                                  className={styles.textarea}
                                  value={editForm.description || ''}
                                  onChange={(e) => updateEditField('description', e.target.value)}
                                  rows={3}
                                />
                              </div>

                              {/* Example (expression-style) */}
                              {activeTab === 'expression-style' && (
                                <div className={styles.ifaceFieldGroup}>
                                  <span className={styles.ifaceFieldLabel}>{s.example}</span>
                                  <textarea
                                    className={styles.textarea}
                                    value={editForm.example || ''}
                                    onChange={(e) => updateEditField('example', e.target.value)}
                                    rows={2}
                                  />
                                </div>
                              )}

                              {/* Items (core-trait / scenario / expression-style) */}
                              {itemsInfo && (
                                <div className={styles.ifaceFieldGroup}>
                                  <div className={styles.csItemsHeader}>
                                    <span className={styles.ifaceFieldLabel}>{itemsInfo.label}</span>
                                    <span className={styles.ifaceFieldHint} style={{ margin: 0 }}>
                                      {(editForm.items || []).length} / {ITEMS_MAX}
                                    </span>
                                  </div>
                                  <div className={styles.csItemsList}>
                                    {(editForm.items || []).map((item, idx) => (
                                      <div key={idx} className={styles.csItemRow}>
                                        <textarea
                                          className={styles.textarea}
                                          value={item}
                                          onChange={(e) => updateEditItem(idx, e.target.value)}
                                          rows={2}
                                        />
                                        {(editForm.items || []).length > 1 && (
                                          <button
                                            type="button"
                                            className={styles.csRemoveItemBtn}
                                            onClick={() => removeEditItem(idx)}
                                            title={s.remove}
                                          >
                                            &minus;
                                          </button>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                  {(editForm.items || []).length < ITEMS_MAX && (
                                    <button
                                      type="button"
                                      className={styles.csAddItemBtn}
                                      onClick={addEditItem}
                                    >
                                      {s.addItem}
                                    </button>
                                  )}
                                </div>
                              )}

                              {/* Edit Actions */}
                              <div className={styles.cslEditActions}>
                                <Button variant="ghost" size="sm" onClick={cancelEdit}>
                                  {s.cancelEdit}
                                </Button>
                                <Button variant="primary" size="sm" onClick={saveEdit}>
                                  {s.saveEdit}
                                </Button>
                              </div>
                            </>
                          ) : (
                            /* ── View Mode ── */
                            <>
                              {/* Key */}
                              <div className={styles.cslDetailField}>
                                <span className={styles.cslDetailLabel}>{s.key}</span>
                                <span className={`${styles.cslDetailValue} ${styles.cslDetailMono}`}>
                                  {entry.key}
                                </span>
                              </div>

                              {/* Name (if different from key) */}
                              {entry.name && entry.name !== entry.key && (
                                <div className={styles.cslDetailField}>
                                  <span className={styles.cslDetailLabel}>{s.name}</span>
                                  <span className={styles.cslDetailValue}>{entry.name}</span>
                                </div>
                              )}

                              {/* Description */}
                              {entry.description && (
                                <div className={styles.cslDetailField}>
                                  <span className={styles.cslDetailLabel}>{s.description}</span>
                                  <span className={styles.cslDetailValue}>{toStr(entry.description)}</span>
                                </div>
                              )}

                              {/* Example */}
                              {entry.example && (
                                <div className={styles.cslDetailField}>
                                  <span className={styles.cslDetailLabel}>{s.example}</span>
                                  <span className={styles.cslDetailValue}>{entry.example}</span>
                                </div>
                              )}

                              {/* Items list */}
                              {itemsInfo && entry[itemsInfo.field] && entry[itemsInfo.field].length > 0 && (
                                <div className={styles.cslDetailField}>
                                  <span className={styles.cslDetailLabel}>{itemsInfo.label}</span>
                                  <div className={styles.cslChipList}>
                                    {entry[itemsInfo.field].map((item, idx) => (
                                      <span key={idx} className={styles.cslChip}>{item}</span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}

                      {i < entries.length - 1 && <div className={styles.ifaceDivider} />}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ═══ Bottom Action ═══ */}
        {onOpenCreate && entries.length > 0 && (
          <div className={styles.cslLinkRow}>
            <button type="button" className={styles.cslLinkBtn} onClick={onOpenCreate}>
              {s.createNewPlus}
            </button>
          </div>
        )}

      </OverlayBody>
    </Overlay>
  );
}
