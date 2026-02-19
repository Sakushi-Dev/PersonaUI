// ── UserProfileOverlay ──
// User name, avatar, type, gender, interests, about — matches legacy profile

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
import { getAvailableOptions } from '../../services/personaApi';
import { useOverlay } from '../../hooks/useOverlay';
import styles from './Overlays.module.css';

const GENDER_OPTIONS = [
  { value: 'Männlich', label: 'Männlich' },
  { value: 'Weiblich', label: 'Weiblich' },
  { value: 'Divers', label: 'Divers' },
];

export default function UserProfileOverlay({ open, onClose, onOpenAvatarEditor, avatarRefreshKey }) {
  const [name, setName] = useState('User');
  const [avatar, setAvatar] = useState(null);
  const [avatarType, setAvatarType] = useState(null);
  const [gender, setGender] = useState('');
  const [interestedIn, setInterestedIn] = useState([]);
  const [userInfo, setUserInfo] = useState('');
  const [userType, setUserType] = useState(null);
  const [userTypeDescription, setUserTypeDescription] = useState(null);
  const [saving, setSaving] = useState(false);

  // Type options from backend
  const [availableTypes, setAvailableTypes] = useState([]);
  const [typeDetails, setTypeDetails] = useState({});
  const [customKeys, setCustomKeys] = useState([]);

  useEffect(() => {
    if (open) {
      // Load profile + available options in parallel
      Promise.all([
        getUserProfile(),
        getAvailableOptions(),
      ]).then(([profileData, optionsData]) => {
        // Profile
        const p = profileData.profile || profileData;
        setName(p.user_name || 'User');
        setAvatar(p.user_avatar || null);
        setAvatarType(p.user_avatar_type || null);
        setGender(p.user_gender || '');
        setInterestedIn(p.user_interested_in || []);
        setUserInfo(p.user_info || '');
        setUserType(p.user_type || null);
        setUserTypeDescription(p.user_type_description || null);

        // Options
        const opts = optionsData.options || optionsData;
        setAvailableTypes(opts.persona_types || []);
        setTypeDetails(optionsData.details?.persona_types || {});
        setCustomKeys(optionsData.custom_keys?.persona_types || []);
      }).catch(() => {});
    }
  }, [open]);

  // Re-load avatar when changed from the gallery editor
  useEffect(() => {
    if (open && avatarRefreshKey > 0) {
      getUserProfile().then((data) => {
        const p = data.profile || data;
        setAvatar(p.user_avatar || null);
        setAvatarType(p.user_avatar_type || null);
      }).catch(() => {});
    }
  }, [avatarRefreshKey, open]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await updateUserProfile({
        user_name: name,
        user_avatar: avatar,
        user_avatar_type: avatarType,
        user_gender: gender,
        user_interested_in: interestedIn,
        user_info: userInfo,
        user_type: userType,
        user_type_description: userTypeDescription,
      });
      onClose();
    } catch (err) {
      console.error('Profile save failed:', err);
    } finally {
      setSaving(false);
    }
  }, [name, avatar, avatarType, gender, interestedIn, userInfo, userType, userTypeDescription, onClose]);

  const handleAvatarClick = () => {
    onOpenAvatarEditor?.('user');
  };

  const handleRemoveAvatar = () => {
    setAvatar(null);
    setAvatarType(null);
  };

  const handleSelectType = (type) => {
    const typeName = typeof type === 'string' ? type : type.key || type.name;
    if (userType === typeName) {
      // Deselect
      setUserType(null);
      setUserTypeDescription(null);
    } else {
      setUserType(typeName);
      setUserTypeDescription(typeDetails[typeName] || null);
    }
  };

  const handleRemoveType = () => {
    setUserType(null);
    setUserTypeDescription(null);
  };

  return (
    <Overlay open={open} onClose={onClose} width="480px">
      <OverlayHeader title="Mein Profil" onClose={onClose} />
      <OverlayBody>
        {/* Profile Card: Avatar + Name */}
        <div className={styles.profileCard}>
          <div className={styles.profileCardTop}>
            <div className={styles.profileAvatarWrapper}>
              <Avatar
                src={avatar}
                type={avatarType}
                name={name}
                size={88}
                onClick={handleAvatarClick}
                className={styles.clickableAvatar}
              />
            </div>
            <div className={styles.profileNameArea}>
              <input
                className={styles.textInput}
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={30}
                placeholder="Dein Name"
              />
              <span className={styles.hint}>Dein Anzeigename im Chat</span>
            </div>
          </div>
          {avatar && (
            <div className={styles.avatarActions}>
              <Button variant="danger" size="sm" onClick={handleRemoveAvatar}>
                Avatar entfernen
              </Button>
            </div>
          )}
        </div>

        <div className={styles.sectionDivider} />

        {/* User Type Section — pills with description only for selected */}
        {availableTypes.length > 0 && (
          <>
            <FormGroup label="Mein Typ">
              <div className={styles.typePills}>
                {availableTypes.map((t, i) => {
                  const typeName = typeof t === 'string' ? t : t.key || t.name;
                  const isActive = userType === typeName;
                  return (
                    <button
                      key={i}
                      type="button"
                      className={`${styles.typePill} ${isActive ? styles.typePillActive : ''}`}
                      onClick={() => handleSelectType(t)}
                    >
                      {typeName}
                    </button>
                  );
                })}
              </div>
              {userType && userTypeDescription && (
                <div className={styles.typeDescBox}>
                  <span className={styles.typeDescText}>{userTypeDescription}</span>
                </div>
              )}
            </FormGroup>

            <div className={styles.sectionDivider} />
          </>
        )}

        {/* Gender & Interests */}
        <FormGroup label="Geschlecht">
          <ChipSelector
            options={GENDER_OPTIONS}
            value={gender}
            onChange={setGender}
          />
        </FormGroup>

        <div style={{ height: 12 }} />

        <FormGroup label="Interessiert an">
          <ChipSelector
            options={GENDER_OPTIONS}
            value={interestedIn}
            onChange={setInterestedIn}
            multiple
          />
        </FormGroup>

        <div className={styles.sectionDivider} />

        {/* About */}
        <FormGroup label="Über mich" charCount={userInfo.length} maxLength={500}>
          <textarea
            className={styles.textarea}
            value={userInfo}
            onChange={(e) => setUserInfo(e.target.value)}
            maxLength={500}
            rows={3}
            placeholder="Schreibe etwas über dich... Interessen, Besonderheiten, Kontext für die KI"
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
