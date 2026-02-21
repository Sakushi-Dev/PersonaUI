/**
 * UserProfileManager - Handles user profile settings (avatar, name, info)
 * Updates chat bubbles live when profile is saved.
 * Avatar: clicking the avatar opens the shared AvatarManager gallery/upload overlay.
 */
export class UserProfileManager {
    constructor(dom, avatarManager) {
        this.dom = dom;
        this.avatarManager = avatarManager; // shared AvatarManager instance
        this.profile = {};
        this.selectedAvatar = null;
        this.selectedAvatarType = null;
    }

    /* ========== OPEN / CLOSE ========== */

    async open() {
        try {
            const profileRes = await fetch('/api/user-profile');
            const profileData = await profileRes.json();

            if (profileData.success) {
                this.profile = profileData.profile;
            }

            this.selectedAvatar = null;
            this.selectedAvatarType = null;
            this._render();
            document.getElementById('user-profile-overlay').classList.remove('hidden');
        } catch (error) {
            console.error('Fehler beim Laden des User-Profils:', error);
        }
    }

    close() {
        document.getElementById('user-profile-overlay').classList.add('hidden');
        // Avatar-Aktionen & Galerie ausblenden
        document.getElementById('up-avatar-actions')?.classList.add('hidden');
        document.getElementById('user-avatar-gallery')?.classList.add('hidden');
    }

    /* ========== RENDER ========== */

    _render() {
        // Name
        const nameInput = document.getElementById('user-name-input');
        if (nameInput) nameInput.value = this.profile.user_name || 'User';

        // Info + counter
        const infoInput = document.getElementById('user-info-input');
        const infoCount = document.getElementById('user-info-count');
        if (infoInput) {
            infoInput.value = this.profile.user_info || '';
            if (infoCount) infoCount.textContent = (this.profile.user_info || '').length;
        }

        this._updateAvatarPreview();
        this._renderGender();
        this._renderInterestedIn();
    }

    /* ========== AVATAR ========== */

    _updateAvatarPreview() {
        const preview = document.getElementById('user-avatar-preview');
        const placeholder = document.getElementById('user-avatar-placeholder');
        if (!preview) return;

        const avatar = this.selectedAvatar || this.profile.user_avatar;
        const avatarType = this.selectedAvatarType || this.profile.user_avatar_type;

        if (avatar) {
            const path = avatarType === 'custom'
                ? `/static/images/custom/${avatar}`
                : `/static/images/avatars/${avatar}`;
            preview.style.backgroundImage = `url('${path}')`;
            preview.style.backgroundSize = 'cover';
            preview.style.backgroundPosition = 'center';
            if (placeholder) placeholder.style.display = 'none';
            // Show remove button
            document.getElementById('up-avatar-actions')?.classList.remove('hidden');
        } else {
            preview.style.backgroundImage = '';
            if (placeholder) {
                placeholder.style.display = '';
                const name = document.getElementById('user-name-input')?.value || 'User';
                placeholder.textContent = name.charAt(0).toUpperCase();
            }
            // Hide remove button
            document.getElementById('up-avatar-actions')?.classList.add('hidden');
        }
    }

    /**
     * Klick auf Avatar → öffne AvatarManager Gallery für User
     */
    openAvatarGallery() {
        if (!this.avatarManager) return;
        this.avatarManager.openAvatarEditorForUser((avatarData) => {
            this.selectedAvatar = avatarData.avatar;
            this.selectedAvatarType = avatarData.avatar_type;
            this._updateAvatarPreview();
        });
    }

    removeAvatar() {
        this.selectedAvatar = null;
        this.selectedAvatarType = null;
        this.profile.user_avatar = null;
        this.profile.user_avatar_type = null;
        this._updateAvatarPreview();
    }

    /* ========== GENDER / INTERESTED IN ========== */

    _renderGender() {
        const grid = document.getElementById('up-gender-grid');
        if (!grid) return;
        grid.querySelectorAll('.up-gender-chip').forEach(chip => {
            const gender = chip.dataset.gender;
            chip.classList.toggle('active', this.profile.user_gender === gender);
            // Remove old listener by cloning
            const newChip = chip.cloneNode(true);
            chip.parentNode.replaceChild(newChip, chip);
            newChip.addEventListener('click', () => {
                if (this.profile.user_gender === gender) {
                    this.profile.user_gender = null;
                } else {
                    this.profile.user_gender = gender;
                }
                this._renderGender();
            });
        });
    }

    _renderInterestedIn() {
        const grid = document.getElementById('up-interested-grid');
        if (!grid) return;
        const interests = this.profile.user_interested_in || [];
        grid.querySelectorAll('.up-gender-chip').forEach(chip => {
            const interest = chip.dataset.interest;
            chip.classList.toggle('active', interests.includes(interest));
            // Remove old listener by cloning
            const newChip = chip.cloneNode(true);
            chip.parentNode.replaceChild(newChip, chip);
            newChip.addEventListener('click', () => {
                if (!this.profile.user_interested_in) this.profile.user_interested_in = [];
                const idx = this.profile.user_interested_in.indexOf(interest);
                if (idx >= 0) {
                    this.profile.user_interested_in.splice(idx, 1);
                } else {
                    this.profile.user_interested_in.push(interest);
                }
                this._renderInterestedIn();
            });
        });
    }

    /* ========== SAVE & LIVE UPDATE ========== */

    async save() {
        const nameInput = document.getElementById('user-name-input');
        const infoInput = document.getElementById('user-info-input');

        const profileData = {
            user_name: nameInput?.value?.trim() || 'User',
            user_gender: this.profile.user_gender || null,
            user_interested_in: this.profile.user_interested_in || [],
            user_info: infoInput?.value || '',
            user_avatar: this.selectedAvatar || this.profile.user_avatar,
            user_avatar_type: this.selectedAvatarType || this.profile.user_avatar_type
        };

        try {
            const res = await fetch('/api/user-profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(profileData)
            });
            const data = await res.json();
            if (data.success) {
                this.profile = data.profile;
                this._updateChatBubbles();
                this.close();
            } else {
                alert(data.error || 'Fehler beim Speichern');
            }
        } catch (e) {
            console.error('Profil-Speichern Fehler:', e);
        }
    }

    /**
     * Aktualisiere alle User-Bubbles im Chat live
     */
    _updateChatBubbles() {
        const userName = this.profile.user_name || 'User';
        const avatar = this.profile.user_avatar;
        const avatarType = this.profile.user_avatar_type;

        // Update window.userProfile for new messages
        window.userProfile = {
            user_name: userName,
            user_avatar: avatar,
            user_avatar_type: avatarType
        };

        // Update all existing user bubbles
        document.querySelectorAll('.message.user-message').forEach(msg => {
            // Update sender name
            const sender = msg.querySelector('.message-sender');
            if (sender) sender.textContent = userName;

            // Update avatar
            const avatarDiv = msg.querySelector('.message-avatar');
            if (avatarDiv) {
                if (avatar) {
                    const path = avatarType === 'custom'
                        ? `/static/images/custom/${avatar}`
                        : `/static/images/avatars/${avatar}`;
                    avatarDiv.style.backgroundImage = `url('${path}')`;
                    avatarDiv.style.backgroundSize = 'cover';
                    avatarDiv.style.backgroundPosition = 'center';
                    // Remove text child
                    const txt = avatarDiv.querySelector('.avatar-text');
                    if (txt) txt.style.display = 'none';
                } else {
                    avatarDiv.style.backgroundImage = '';
                    let txt = avatarDiv.querySelector('.avatar-text');
                    if (!txt) {
                        txt = document.createElement('span');
                        txt.className = 'avatar-text';
                        avatarDiv.appendChild(txt);
                    }
                    txt.style.display = '';
                    txt.textContent = userName.charAt(0).toUpperCase();
                }
            }
        });
    }

    /* ========== EVENT LISTENERS ========== */

    setupEventListeners() {
        // Close
        document.getElementById('close-user-profile')?.addEventListener('click', () => this.close());

        // Save
        document.getElementById('save-user-profile-btn')?.addEventListener('click', () => this.save());

        // Avatar click → open gallery overlay
        document.getElementById('user-avatar-preview')?.addEventListener('click', () => this.openAvatarGallery());

        // Remove avatar
        document.getElementById('user-avatar-remove-btn')?.addEventListener('click', () => this.removeAvatar());

        // Info char counter
        const infoInput = document.getElementById('user-info-input');
        const infoCount = document.getElementById('user-info-count');
        if (infoInput && infoCount) {
            infoInput.addEventListener('input', () => {
                const len = infoInput.value.length;
                infoCount.textContent = len;
                infoCount.parentElement.classList.toggle('over-limit', len > 500);
            });
        }

        // Name → update avatar placeholder
        const nameInput = document.getElementById('user-name-input');
        if (nameInput) {
            nameInput.addEventListener('input', () => {
                const placeholder = document.getElementById('user-avatar-placeholder');
                if (placeholder && !this.profile.user_avatar && !this.selectedAvatar) {
                    placeholder.textContent = (nameInput.value || 'U').charAt(0).toUpperCase();
                }
            });
        }

        // Overlay background click → close
        document.getElementById('user-profile-overlay')?.addEventListener('click', (e) => {
            if (e.target.id === 'user-profile-overlay') this.close();
        });
    }
}
