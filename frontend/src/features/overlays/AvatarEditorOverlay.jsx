// ── AvatarEditorOverlay ──
// Avatar gallery selection + custom upload with crop

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { UserIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import AvatarCropper from '../../components/AvatarCropper/AvatarCropper';
import Spinner from '../../components/Spinner/Spinner';
import { getAvailableAvatars, uploadAvatar, saveAvatar, saveUserAvatar, deleteAvatar } from '../../services/avatarApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function AvatarEditorOverlay({ open, onClose, personaId, target = 'persona', onSaved, stacked }) {
  const [avatars, setAvatars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('gallery'); // 'gallery' | 'crop'
  const [selectedFile, setSelectedFile] = useState(null);
  const [selected, setSelected] = useState(null); // highlighted gallery avatar
  const [saving, setSaving] = useState(false);
  const { t } = useLanguage();
  const s = t('avatarEditor');
  const sc = t('common');

  const refreshGallery = useCallback(() => {
    setLoading(true);
    getAvailableAvatars()
      .then((data) => setAvatars(data.avatars || data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (open) {
      setView('gallery');
      setSelectedFile(null);
      setSelected(null);
      refreshGallery();
    }
  }, [open, refreshGallery]);

  // ── Confirm selected gallery avatar ──
  const handleConfirmSelection = useCallback(async () => {
    if (!selected) return;
    setSaving(true);
    try {
      if (target === 'user') {
        await saveUserAvatar(selected.filename, selected.type);
      } else if (target !== 'persona') {
        await saveAvatar(personaId, selected.filename, selected.type);
      }
      onSaved?.(selected.filename, selected.type);
      onClose();
    } catch (err) {
      console.error('Avatar save failed:', err);
    } finally {
      setSaving(false);
    }
  }, [selected, personaId, target, onSaved, onClose]);

  // ── Delete custom avatar ──
  const handleDelete = useCallback(async (avatar, e) => {
    e.stopPropagation();
    try {
      await deleteAvatar(avatar.filename);
      if (selected?.filename === avatar.filename) setSelected(null);
      refreshGallery();
    } catch (err) {
      console.error('Avatar delete failed:', err);
    }
  }, [selected, refreshGallery]);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setView('crop');
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const file = e.dataTransfer?.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setView('crop');
    }
  }, []);

  const handleCropSave = useCallback(async (croppedBlob) => {
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append('file', croppedBlob, 'avatar.jpg');

      const result = await uploadAvatar(formData);
      const filename = result.filename || result.avatar;

      if (target === 'user') {
        await saveUserAvatar(filename, 'custom');
      } else if (target !== 'persona') {
        await saveAvatar(personaId, filename, 'custom');
      }
      onSaved?.(filename, 'custom');

      // Go back to gallery and refresh the avatar list
      setSelectedFile(null);
      setSelected(null);
      setLoading(true);
      setView('gallery');
      refreshGallery();
    } catch (err) {
      console.error('Avatar upload failed:', err);
    } finally {
      setSaving(false);
    }
  }, [personaId, target, onSaved, refreshGallery]);

  return (
    <Overlay open={open} onClose={onClose} width="560px" stacked={stacked}>
      <OverlayHeader
        title={view === 'crop' ? s.titleCrop : s.titleSelect}
        icon={<UserIcon size={20} />}
        onClose={onClose}
      />
      <OverlayBody>
        {view === 'gallery' ? (
          <>
            {/* Upload zone */}
            <div
              className={styles.dropZone}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => document.getElementById('avatar-file-input')?.click()}
            >
              <span className={styles.bigIcon}>📷</span>
              <p>{s.dropText}</p>
              <p className={styles.hint}>{s.dropHint}</p>
              <input
                id="avatar-file-input"
                type="file"
                accept=".png,.jpg,.jpeg,.webp"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
            </div>

            <div className={styles.divider}>{s.galleryDivider}</div>

            {loading ? (
              <Spinner />
            ) : (
              <div className={styles.avatarGallery}>
                {avatars.map((av, i) => (
                  <div key={i} className={styles.avatarThumbWrap}>
                    <button
                      className={`${styles.avatarThumb} ${selected?.filename === av.filename ? styles.avatarThumbSelected : ''}`}
                      onClick={() => setSelected(av)}
                      disabled={saving}
                    >
                      <img
                        src={av.type === 'custom' ? `/avatar/costum/${av.filename}` : `/avatar/${av.filename}`}
                        alt={av.filename}
                      />
                    </button>
                    {av.type === 'custom' && (
                      <button
                        className={styles.avatarDeleteBtn}
                        onClick={(e) => handleDelete(av, e)}
                        title={sc.delete}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <AvatarCropper
            file={selectedFile}
            onSave={handleCropSave}
            onCancel={() => setView('gallery')}
          />
        )}
      </OverlayBody>
      {view === 'gallery' && (
        <OverlayFooter>
          <Button variant="primary" onClick={handleConfirmSelection} disabled={!selected || saving}>
            {s.confirmSelect}
          </Button>
          <Button variant="secondary" onClick={onClose}>{sc.cancel}</Button>
        </OverlayFooter>
      )}
    </Overlay>
  );
}
