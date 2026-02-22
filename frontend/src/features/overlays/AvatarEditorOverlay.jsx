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
import { getAvailableAvatars, uploadAvatar, saveAvatar, saveUserAvatar } from '../../services/avatarApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

export default function AvatarEditorOverlay({ open, onClose, personaId, target = 'persona', onSaved, stacked }) {
  const [avatars, setAvatars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('gallery'); // 'gallery' | 'crop'
  const [selectedFile, setSelectedFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const { t } = useLanguage();
  const s = t('avatarEditor');
  const sc = t('common');

  useEffect(() => {
    if (open) {
      setView('gallery');
      setSelectedFile(null);
      setLoading(true);
      getAvailableAvatars()
        .then((data) => setAvatars(data.avatars || data || []))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [open]);

  const handleSelectGallery = useCallback(async (avatar) => {
    setSaving(true);
    try {
      if (target === 'user') {
        await saveUserAvatar(avatar.filename, avatar.type);
      } else if (target !== 'persona') {
        // For persona creator/editor, skip server save — avatar is stored locally
        // and included in the persona save payload
        await saveAvatar(personaId, avatar.filename, avatar.type);
      }
      onSaved?.(avatar.filename, avatar.type);
      onClose();
    } catch (err) {
      console.error('Avatar save failed:', err);
    } finally {
      setSaving(false);
    }
  }, [personaId, target, onSaved, onClose]);

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
      formData.append('crop_data', JSON.stringify({ x: 0, y: 0, size: 1024 }));

      const result = await uploadAvatar(formData);
      const filename = result.filename || result.avatar;

      if (target === 'user') {
        await saveUserAvatar(filename, 'custom');
      } else if (target !== 'persona') {
        // For persona creator/editor, skip server save
        await saveAvatar(personaId, filename, 'custom');
      }
      onSaved?.(filename, 'custom');
      onClose();
    } catch (err) {
      console.error('Avatar upload failed:', err);
    } finally {
      setSaving(false);
    }
  }, [personaId, target, onSaved, onClose]);

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
                  <button
                    key={i}
                    className={styles.avatarThumb}
                    onClick={() => handleSelectGallery(av)}
                    disabled={saving}
                  >
                    <img
                      src={`/static/images/avatars/${av.filename}`}
                      alt={av.filename}
                    />
                  </button>
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
          <Button variant="secondary" onClick={onClose}>{sc.cancel}</Button>
        </OverlayFooter>
      )}
    </Overlay>
  );
}
