// ── User Context ──

import { createContext, useState, useCallback, useEffect } from 'react';
import { getUserProfile, updateUserProfile } from '../services/userProfileApi';

export const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [profile, setProfile] = useState({
    user_name: '',
    user_avatar: null,
    user_avatar_type: 'none',
  });

  useEffect(() => {
    getUserProfile()
      .then((data) => {
        if (data.success !== false) {
          setProfile(data.profile || data);
        }
      })
      .catch((err) => console.warn('Failed to load user profile:', err));
  }, []);

  const updateProfile = useCallback(async (updates) => {
    try {
      const data = await updateUserProfile(updates);
      if (data.success !== false) {
        setProfile((prev) => ({ ...prev, ...updates }));
      }
      return data;
    } catch (err) {
      console.warn('Failed to update profile:', err);
      throw err;
    }
  }, []);

  const setAvatar = useCallback((avatarData, avatarType) => {
    setProfile((prev) => ({
      ...prev,
      user_avatar: avatarData,
      user_avatar_type: avatarType,
    }));
  }, []);

  const value = { profile, setProfile, updateProfile, setAvatar };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}
