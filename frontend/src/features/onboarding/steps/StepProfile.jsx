// ── Step: Profile (1/4) ──

import { useState, useEffect } from 'react';
import FormGroup from '../../../components/FormGroup/FormGroup';
import ChipSelector from '../../../components/ChipSelector/ChipSelector';
import Avatar from '../../../components/Avatar/Avatar';
import Button from '../../../components/Button/Button';
import { getAvailableOptions } from '../../../services/personaApi';
import styles from './Steps.module.css';

const GENDER_OPTIONS = [
  { value: 'männlich', label: 'Männlich' },
  { value: 'weiblich', label: 'Weiblich' },
  { value: 'divers', label: 'Divers' },
];

export default function StepProfile({ data, onChange, onNext, onBack }) {
  const [typeOptions, setTypeOptions] = useState([]);

  useEffect(() => {
    getAvailableOptions().then((opts) => {
      const types = (opts.persona_types || []).map((t) => ({
        value: typeof t === 'string' ? t : t.key,
        label: typeof t === 'string' ? t : t.name || t.key,
      }));
      setTypeOptions(types);
    }).catch(() => {});
  }, []);

  const update = (field, value) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className={styles.step}>
      <h2 className={styles.title}>Dein Profil <span className={styles.stepNum}>(1/4)</span></h2>
      <p className={styles.subtitle}>Erzähl uns etwas über dich</p>

      <div className={styles.avatarSection}>
        <Avatar
          src={data.user_avatar}
          type={data.user_avatar_type}
          name={data.user_name || 'U'}
          size={80}
        />
      </div>

      <FormGroup label="Name *" charCount={data.user_name?.length} maxLength={30}>
        <input
          className={styles.input}
          type="text"
          value={data.user_name}
          onChange={(e) => update('user_name', e.target.value)}
          maxLength={30}
          placeholder="Dein Name"
        />
      </FormGroup>

      {typeOptions.length > 0 && (
        <FormGroup label="Typ (optional)">
          <ChipSelector
            options={typeOptions}
            value={data.user_type}
            onChange={(v) => update('user_type', v)}
          />
        </FormGroup>
      )}

      <FormGroup label="Geschlecht (optional)">
        <ChipSelector
          options={GENDER_OPTIONS}
          value={data.user_gender}
          onChange={(v) => update('user_gender', v)}
        />
      </FormGroup>

      <FormGroup label="Interessiert an (optional)">
        <ChipSelector
          options={GENDER_OPTIONS}
          value={data.user_interested_in}
          onChange={(v) => update('user_interested_in', v)}
          multiple
        />
      </FormGroup>

      <FormGroup label="Über mich (optional)" charCount={data.user_info?.length} maxLength={500}>
        <textarea
          className={styles.textarea}
          value={data.user_info}
          onChange={(e) => update('user_info', e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="Erzähle etwas über dich..."
        />
      </FormGroup>

      <div className={styles.footer}>
        <Button variant="secondary" onClick={onBack}>Zurück</Button>
        <Button variant="primary" onClick={onNext} disabled={!data.user_name?.trim()}>
          Weiter
        </Button>
      </div>
    </div>
  );
}
