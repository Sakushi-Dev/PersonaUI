// ── Step: Profile (1/4) – Legacy 1:1 ──

import { useState, useEffect, useCallback } from 'react';
import AvatarCropper from '../../../components/AvatarCropper/AvatarCropper';
import { getAvailableOptions } from '../../../services/personaApi';
import { getAvailableAvatars, uploadAvatar } from '../../../services/avatarApi';
import { API_BASE_URL } from '../../../utils/constants';
import styles from './Steps.module.css';

export default function StepProfile({ data, onChange, onNext, onBack }) {
  const [typeOptions, setTypeOptions] = useState([]);
  const [typeDetails, setTypeDetails] = useState({});

  // Avatar gallery state
  const [showGallery, setShowGallery] = useState(false);
  const [galleryView, setGalleryView] = useState('select'); // 'select' | 'crop'
  const [avatars, setAvatars] = useState([]);
  const [cropFile, setCropFile] = useState(null);

  useEffect(() => {
    getAvailableOptions().then((opts) => {
      const types = opts.options?.persona_types || opts.persona_types || [];
      const details = opts.details?.persona_types || {};
      setTypeOptions(types);
      setTypeDetails(details);
    }).catch(() => {});
  }, []);

  const update = (field, value) => {
    onChange((prev) => ({ ...prev, [field]: value }));
  };

  // Avatar preview helper
  const avatarSrc = data.user_avatar
    ? data.user_avatar_type === 'custom'
      ? `${API_BASE_URL}/static/images/custom/${data.user_avatar}`
      : `${API_BASE_URL}/static/images/avatars/${data.user_avatar}`
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
    if (file.size > 10 * 1024 * 1024) { alert('File too large (max 10MB)'); return; }
    setCropFile(file);
    setGalleryView('crop');
  };

  const handleCropSave = useCallback(async (croppedBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', croppedBlob, 'avatar.jpg');
      formData.append('crop_data', JSON.stringify({ x: 0, y: 0, size: 1024 }));
      const result = await uploadAvatar(formData);
      const filename = result.filename || result.avatar;
      update('user_avatar', filename);
      update('user_avatar_type', 'custom');
      closeGallery();
    } catch (err) {
      console.error('Upload error:', err);
      alert('Connection error');
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

  // ── Type chip handler ──
  const toggleType = (type) => {
    if (data.user_type === type) {
      update('user_type', null);
      update('user_type_description', null);
    } else {
      update('user_type', type);
      update('user_type_description', typeDetails[type] || null);
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.cardStep}>1 / 6</span>
        <h2>Your Profile</h2>
        <p className={styles.cardDesc}>This is how your personas get to know you.</p>
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
              Remove Avatar
            </button>
          )}
        </div>

        {/* Avatar Gallery Overlay */}
        {showGallery && (
          <div className={styles.galleryOverlay} onClick={(e) => { if (e.target === e.currentTarget) closeGallery(); }}>
            <div className={styles.galleryCard}>
              <div className={styles.galleryHeader}>
                <h3>Choose Avatar</h3>
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
                    <span className={styles.dropzoneText}>Drag your own image here</span>
                    <span className={styles.dropzoneHint}>or click to browse</span>
                  </div>
                  <input
                    type="file"
                    id="ob-avatar-file"
                    accept=".png,.jpg,.jpeg,.webp"
                    style={{ display: 'none' }}
                    onChange={(e) => handleFileSelect(e.target.files)}
                  />

                  <div className={styles.avatarDivider}><span>or choose from gallery</span></div>

                  <div className={styles.avatarGrid}>
                    {avatars.map((av, i) => (
                      <div
                        key={i}
                        className={`${styles.avatarOption} ${data.user_avatar === av.filename ? styles.avatarSelected : ''}`}
                        onClick={() => selectGalleryAvatar(av.filename, av.type)}
                      >
                        <img
                          src={av.type === 'custom'
                            ? `${API_BASE_URL}/static/images/custom/${av.filename}`
                            : `${API_BASE_URL}/static/images/avatars/${av.filename}`}
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
          <label className={styles.label}>Your Name *</label>
          <input
            className={styles.input}
            type="text"
            value={data.user_name}
            onChange={(e) => update('user_name', e.target.value)}
            maxLength={30}
            placeholder="What would you like to be called?"
          />
        </div>

        {/* Typ */}
        {typeOptions.length > 0 && (
          <div className={styles.fieldGroup}>
            <label className={styles.label}>Your Type <span className={styles.labelOptional}>(optional)</span></label>
            <div className={styles.typeGrid}>
              {typeOptions.map((type) => (
                <div
                  key={type}
                  className={`${styles.typeChip} ${data.user_type === type ? styles.chipActive : ''}`}
                  title={typeDetails[type] || ''}
                  onClick={() => toggleType(type)}
                >
                  {type}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Geschlecht */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Your Gender <span className={styles.labelOptional}>(optional)</span></label>
          <div className={styles.genderGrid}>
            {['Male', 'Female', 'Other'].map((g) => (
              <div
                key={g}
                className={`${styles.typeChip} ${data.user_gender === g ? styles.chipActive : ''}`}
                onClick={() => toggleGender(g)}
              >
                {g}
              </div>
            ))}
          </div>
        </div>

        {/* Interessiere mich für */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Interested In <span className={styles.labelOptional}>(you can select multiple, optional)</span></label>
          <div className={styles.genderGrid}>
            {['Male', 'Female', 'Other'].map((g) => (
              <div
                key={g}
                className={`${styles.typeChip} ${(data.user_interested_in || []).includes(g) ? styles.chipActive : ''}`}
                onClick={() => toggleInterest(g)}
              >
                {g}
              </div>
            ))}
          </div>
        </div>

        {/* Über mich */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>About Me <span className={styles.labelOptional}>(optional)</span></label>
          <textarea
            className={styles.textarea}
            value={data.user_info}
            onChange={(e) => update('user_info', e.target.value)}
            maxLength={500}
            rows={3}
            placeholder="Tell us something about yourself... interests, quirks – the more your personas know about you, the better."
          />
          <div className={styles.charCounter}>
            <span>{(data.user_info || '').length}</span>/500
          </div>
        </div>
      </div>
      <div className={styles.cardFooter}>
        <button className={styles.btnGhost} onClick={onBack}>Back</button>
        <button className={styles.btnPrimary} onClick={onNext} disabled={!data.user_name?.trim()}>Next</button>
      </div>
    </div>
  );
}
