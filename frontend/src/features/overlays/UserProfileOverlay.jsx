// ── UserProfileOverlay ──
// User name, avatar, gender, interests, about

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import FormGroup from '../../components/FormGroup/FormGroup';
import ChipSelector from '../../components/ChipSelector/ChipSelector';
import Avatar from '../../components/Avatar/Avatar';
import Button from '../../components/Button/Button';
import { getUserProfile, updateUserProfile } from '../../services/userProfileApi';
import { useOverlay } from '../../hooks/useOverlay';
import styles from './Overlays.module.css';

const GENDER_OPTIONS = [
  { value: 'männlich', label: 'Männlich' },
  { value: 'weiblich', label: 'Weiblich' },
  { value: 'divers', label: 'Divers' },
];

export default function UserProfileOverlay({ open, onClose, onOpenAvatarEditor }) {
  const [name, setName] = useState('User');
  const [avatar, setAvatar] = useState(null);
  const [avatarType, setAvatarType] = useState(null);
  const [gender, setGender] = useState('');
  const [interestedIn, setInterestedIn] = useState([]);
  const [userInfo, setUserInfo] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      getUserProfile().then((data) => {
        const p = data.profile || data;
        setName(p.user_name || 'User');
        setAvatar(p.user_avatar || null);
        setAvatarType(p.user_avatar_type || null);
        setGender(p.user_gender || '');
        setInterestedIn(p.user_interested_in || []);
        setUserInfo(p.user_info || '');
      }).catch(() => {});
    }
  }, [open]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await updateUserProfile({
        user_name: name,
        user_gender: gender,
        user_interested_in: interestedIn,
        user_info: userInfo,
      });
      onClose();
    } catch (err) {
      console.error('Profile save failed:', err);
    } finally {
      setSaving(false);
    }
  }, [name, gender, interestedIn, userInfo, onClose]);

  const handleAvatarClick = () => {
    onOpenAvatarEditor?.('user');
  };

  return (
    <Overlay open={open} onClose={onClose} width="480px">
      <OverlayHeader title="Mein Profil" onClose={onClose} />
      <OverlayBody>
        {/* Avatar */}
        <div className={styles.profileAvatar}>
          <Avatar
            src={avatar}
            type={avatarType}
            name={name}
            size={80}
            onClick={handleAvatarClick}
            className={styles.clickableAvatar}
          />
          <p className={styles.hint}>Klicken zum Ändern</p>
        </div>

        <FormGroup label="Name" charCount={name.length} maxLength={30}>
          <input
            className={styles.textInput}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={30}
            placeholder="Dein Name"
          />
        </FormGroup>

        <FormGroup label="Geschlecht">
          <ChipSelector
            options={GENDER_OPTIONS}
            value={gender}
            onChange={setGender}
          />
        </FormGroup>

        <FormGroup label="Interessiert an">
          <ChipSelector
            options={GENDER_OPTIONS}
            value={interestedIn}
            onChange={setInterestedIn}
            multiple
          />
        </FormGroup>

        <FormGroup label="Über mich" charCount={userInfo.length} maxLength={500}>
          <textarea
            className={styles.textarea}
            value={userInfo}
            onChange={(e) => setUserInfo(e.target.value)}
            maxLength={500}
            rows={3}
            placeholder="Erzähle etwas über dich..."
          />
        </FormGroup>
      </OverlayBody>
      <OverlayFooter>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Speichert...' : 'Profil speichern'}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
