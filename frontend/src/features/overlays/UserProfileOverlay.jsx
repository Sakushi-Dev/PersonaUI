// ── UserProfileOverlay ──
// User name, avatar, type, gender, interests, about — matches legacy profile

import { useState, useEffect, useCallback } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { UserIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import ChipSelector from '../../components/ChipSelector/ChipSelector';
import Avatar from '../../components/Avatar/Avatar';
import Button from '../../components/Button/Button';
import { getUserProfile, updateUserProfile } from '../../services/userProfileApi';
import { useLanguage } from '../../hooks/useLanguage';
import styles from './Overlays.module.css';

const PERSONA_LANGUAGE_OPTIONS = [
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

export default function UserProfileOverlay({ open, onClose, onOpenAvatarEditor, avatarRefreshKey, panelOnly }) {
  const { t } = useLanguage();
  const s = t('userProfile');
  const sc = t('common');

  const GENDER_OPTIONS = [
    { value: 'Männlich', label: s.male },
    { value: 'Weiblich', label: s.female },
    { value: 'Divers', label: s.diverse },
  ];

  const [name, setName] = useState('User');
  const [avatar, setAvatar] = useState(null);
  const [avatarType, setAvatarType] = useState(null);
  const [gender, setGender] = useState('');
  const [interestedIn, setInterestedIn] = useState([]);
  const [userInfo, setUserInfo] = useState('');
  const [personaLanguage, setPersonaLanguage] = useState('english');
  const [saving, setSaving] = useState(false);


  useEffect(() => {
    if (open) {
      getUserProfile().then((profileData) => {
        const p = profileData.profile || profileData;
        setName(p.user_name || 'User');
        setAvatar(p.user_avatar || null);
        setAvatarType(p.user_avatar_type || null);
        setGender(p.user_gender || '');
        setInterestedIn(p.user_interested_in || []);
        setUserInfo(p.user_info || '');
        setPersonaLanguage(p.persona_language || 'english');
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
        persona_language: personaLanguage,
      });
      onClose();
    } catch (err) {
      console.error('Profile save failed:', err);
    } finally {
      setSaving(false);
    }
  }, [name, avatar, avatarType, gender, interestedIn, userInfo, personaLanguage, onClose]);

  const handleAvatarClick = () => {
    onOpenAvatarEditor?.('user');
  };

  const handleRemoveAvatar = () => {
    setAvatar(null);
    setAvatarType(null);
  };

  return (
    <Overlay open={open} onClose={onClose} width="480px" panelOnly={panelOnly}>
      <OverlayHeader title={s.title} icon={<UserIcon size={20} />} onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Profil ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.profile}</h3>
          <div className={styles.ifaceCard}>
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
                  placeholder={s.namePlaceholder}
                />
                <span className={styles.ifaceToggleHint}>{s.displayNameHint}</span>
              </div>
            </div>
            {avatar && (
              <>
                <div className={styles.ifaceDivider} />
                <div className={styles.profileAvatarAction}>
                  <Button variant="ghost" size="sm" onClick={handleRemoveAvatar}>
                    {s.removeAvatar}
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* ═══ Section: Persoenliches ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.personal}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>{s.gender}</span>
              <ChipSelector
                options={GENDER_OPTIONS}
                value={gender}
                onChange={setGender}
              />
            </div>

            <div className={styles.ifaceDivider} />

            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>{s.interestedIn}</span>
              <span className={styles.ifaceFieldHint}>{s.multiSelect}</span>
              <ChipSelector
                options={GENDER_OPTIONS}
                value={interestedIn}
                onChange={setInterestedIn}
                multiple
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Ueber mich ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.aboutMe}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <div className={styles.profileAboutHeader}>
                <span className={styles.ifaceFieldLabel}>{s.aboutDesc}</span>
                <span className={styles.profileCharCount}>{userInfo.length}/500</span>
              </div>
              <span className={styles.ifaceFieldHint}>{s.aboutHint}</span>
              <textarea
                className={styles.textarea}
                value={userInfo}
                onChange={(e) => setUserInfo(e.target.value)}
                maxLength={500}
                rows={3}
                placeholder={s.aboutPlaceholder}
              />
            </div>
          </div>
        </div>

        {/* ═══ Section: Sprache ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>{s.personaLanguage}</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>{s.personaLanguage}</span>
              <span className={styles.ifaceFieldHint}>{s.personaLanguageHint}</span>
              <select
                className={styles.select}
                value={personaLanguage}
                onChange={(e) => setPersonaLanguage(e.target.value)}
              >
                {PERSONA_LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang.value} value={lang.value}>{lang.label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

      </OverlayBody>
      <OverlayFooter>
        <Button variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? sc.saving : sc.save}
        </Button>
      </OverlayFooter>
    </Overlay>
  );
}
