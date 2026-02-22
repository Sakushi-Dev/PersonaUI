// ── Step: Profile (1/6) ──

import { useState, useCallback, useRef } from 'react';
import AvatarCropper from '../../../components/AvatarCropper/AvatarCropper';
import { getAvailableAvatars, uploadAvatar } from '../../../services/avatarApi';
import { useLanguage } from '../../../hooks/useLanguage';
import styles from './Steps.module.css';

export default function StepProfile({ data, onChange, onNext, onBack }) {
  const { t } = useLanguage();
  const s = t('onboardingProfile');
  const c = t('onboardingCommon');


  // Avatar gallery state
  const galleryMouseDown = useRef(false);
  const [showGallery, setShowGallery] = useState(false);
  const [galleryView, setGalleryView] = useState('select'); // 'select' | 'crop'
  const [avatars, setAvatars] = useState([]);
  const [cropFile, setCropFile] = useState(null);



  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  // Avatar preview helper
  const avatarSrc = data.user_avatar
    ? data.user_avatar_type === 'custom'
      ? `/avatar/costum/${data.user_avatar}`
      : `/avatar/${data.user_avatar}`
    : null;

  const placeholderLetter = (data.user_name || 'U').charAt(0).toUpperCase();

  // ── Avatar gallery ──
  const openGallery = useCallback(async () => {
    setShowGallery(true);
    setGalleryView('select');
    setCropFile(null);
    try {
      const res = await getAvailableAvatars();
      setAvatars(res.avatars || res || []);
    } catch { /* ignore */ }
  }, []);

  const closeGallery = () => {
    setShowGallery(false);
    setCropFile(null);
  };

  const selectGalleryAvatar = (filename, type) => {
    update('user_avatar', filename);
    update('user_avatar_type', type);
    closeGallery();
  };

  const removeAvatar = () => {
    update('user_avatar', null);
    update('user_avatar_type', null);
  };

  const handleFileSelect = (files) => {
    const file = files?.[0];
    if (!file || !file.type.startsWith('image/')) return;
    if (file.size > 10 * 1024 * 1024) { alert(s.fileTooLarge); return; }
    setCropFile(file);
    setGalleryView('crop');
  };

  const handleCropSave = useCallback(async (croppedBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', croppedBlob, 'avatar.jpg');
      // No crop_data — blob is already cropped to a square by AvatarCropper
      const result = await uploadAvatar(formData);
      const filename = result.filename || result.avatar;
      update('user_avatar', filename);
      update('user_avatar_type', 'custom');
      closeGallery();
    } catch (err) {
      console.error('Upload error:', err);
      alert(s.uploadError);
    }
  }, []);

  // ── Gender chip handlers ──
  const toggleGender = (gender) => {
    update('user_gender', data.user_gender === gender ? null : gender);
  };

  const toggleInterest = (interest) => {
    const current = data.user_interested_in || [];
    const idx = current.indexOf(interest);
    if (idx >= 0) {
      update('user_interested_in', current.filter((_, i) => i !== idx));
    } else {
      update('user_interested_in', [...current, interest]);
    }
  };



  // ── Persona language options ──
  const personaLanguages = [
    { value: 'english', label: 'English' },
    { value: 'german', label: 'Deutsch' },
    { value: 'french', label: 'Français' },
    { value: 'spanish', label: 'Español' },
    { value: 'italian', label: 'Italiano' },
    { value: 'portuguese', label: 'Português' },
    { value: 'russian', label: 'Русский' },
    { value: 'japanese', label: '日本語' },
    { value: 'chinese', label: '中文' },
    { value: 'korean', label: '한국어' },
  ];



  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>1 / 6</span>
        <h2>{s.title}</h2>
        <p className={styles.cardDesc}>{s.desc}</p>
      </div>
      <div className={styles.cardBody}>
        {/* Avatar */}
        <div className={styles.avatarGroup}>
          <div
            className={`${styles.avatarUpload} ${avatarSrc ? styles.hasAvatar : ''}`}
            onClick={openGallery}
            title="Click to change avatar"
            style={avatarSrc ? { backgroundImage: `url('${avatarSrc}')`, backgroundSize: 'cover', backgroundPosition: 'center' } : undefined}
          >
            {!avatarSrc && <span className={styles.avatarPlaceholder}>{placeholderLetter}</span>}
            <div className={styles.avatarOverlay}><span>+</span></div>
          </div>
          {avatarSrc && (
            <button className={styles.avatarRemoveBtn} onClick={(e) => { e.stopPropagation(); removeAvatar(); }}>
              {s.removeAvatar}
            </button>
          )}
        </div>

        {/* Avatar Gallery Overlay */}
        {showGallery && (
          <div
            className={styles.galleryOverlay}
            onMouseDown={(e) => { galleryMouseDown.current = e.target === e.currentTarget; }}
            onMouseUp={(e) => { if (galleryMouseDown.current && e.target === e.currentTarget) closeGallery(); galleryMouseDown.current = false; }}
          >
            <div className={styles.galleryCard}>
              <div className={styles.galleryHeader}>
                <h3>{s.chooseAvatar}</h3>
                <button className={styles.galleryClose} onClick={closeGallery}>&times;</button>
              </div>

              {galleryView === 'select' ? (
                <div className={styles.galleryBody}>
                  {/* Upload dropzone */}
                  <div
                    className={styles.dropzone}
                    onClick={() => document.getElementById('ob-avatar-file')?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => { e.preventDefault(); handleFileSelect(e.dataTransfer.files); }}
                  >
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <span className={styles.dropzoneText}>{s.dropzoneText}</span>
                    <span className={styles.dropzoneHint}>{s.dropzoneHint}</span>
                  </div>
                  <input
                    type="file"
                    id="ob-avatar-file"
                    accept=".png,.jpg,.jpeg,.webp"
                    style={{ display: 'none' }}
                    onChange={(e) => handleFileSelect(e.target.files)}
                  />

                  <div className={styles.avatarDivider}><span>{s.galleryDivider}</span></div>

                  <div className={styles.avatarGrid}>
                    {avatars.map((av, i) => (
                      <div
                        key={i}
                        className={`${styles.avatarOption} ${data.user_avatar === av.filename ? styles.avatarSelected : ''}`}
                        onClick={() => selectGalleryAvatar(av.filename, av.type)}
                      >
                        <img
                          src={av.type === 'custom'
                            ? `/avatar/costum/${av.filename}`
                            : `/avatar/${av.filename}`}
                          alt={av.filename}
                          loading="lazy"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className={styles.galleryBody}>
                  <AvatarCropper
                    file={cropFile}
                    onSave={handleCropSave}
                    onCancel={() => setGalleryView('select')}
                  />
                </div>
              )}
            </div>
          </div>
        )}
        

        {/* Name */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.nameLabel}</label>
          <input
            className={styles.input}
            type="text"
            value={data.user_name}
            onChange={(e) => update('user_name', e.target.value)}
            maxLength={30}
            placeholder={s.namePlaceholder}
          />
        </div>

        {/* Geschlecht */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.genderLabel} <span className={styles.labelOptional}>{c.optional}</span></label>
          <div className={styles.genderGrid}>
            {[{ value: 'Male', label: s.genderMale }, { value: 'Female', label: s.genderFemale }, { value: 'Other', label: s.genderOther }].map((g) => (
              <div
                key={g.value}
                className={`${styles.typeChip} ${data.user_gender === g.value ? styles.chipActive : ''}`}
                onClick={() => toggleGender(g.value)}
              >
                {g.label}
              </div>
            ))}
          </div>
        </div>

        {/* Interessiere mich für */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.interestedLabel} <span className={styles.labelOptional}>{s.interestedHint}</span></label>
          <div className={styles.genderGrid}>
            {[{ value: 'Male', label: s.genderMale }, { value: 'Female', label: s.genderFemale }, { value: 'Other', label: s.genderOther }].map((g) => (
              <div
                key={g.value}
                className={`${styles.typeChip} ${(data.user_interested_in || []).includes(g.value) ? styles.chipActive : ''}`}
                onClick={() => toggleInterest(g.value)}
              >
                {g.label}
              </div>
            ))}
          </div>
        </div>

        {/* Persona Language */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.personaLanguageLabel} <span className={styles.labelOptional}>{s.personaLanguageHint}</span></label>
          <select
            className={styles.input}
            value={data.persona_language || 'english'}
            onChange={(e) => update('persona_language', e.target.value)}
          >
            {personaLanguages.map((lang) => (
              <option key={lang.value} value={lang.value}>{lang.label}</option>
            ))}
          </select>
        </div>

        {/* Über mich */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{s.aboutLabel} <span className={styles.labelOptional}>{c.optional}</span></label>
          <textarea
            className={styles.textarea}
            value={data.user_info}
            onChange={(e) => update('user_info', e.target.value)}
            maxLength={500}
            rows={3}
            placeholder={s.aboutPlaceholder}
          />
          <div className={styles.charCounter}>
            <span>{(data.user_info || '').length}</span>/500
          </div>
        </div>
      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>{c.back}</button>
        <button className={styles.btnPrimary} onClick={onNext} disabled={!data.user_name?.trim()}>{c.next}</button>
      </div>
    </div>
  );
}
