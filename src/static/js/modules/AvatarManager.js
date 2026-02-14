/**
 * AvatarManager - Handles avatar gallery selection and crop-on-upload
 * 
 * Flow:
 * - Gallery: User picks from existing 1:1 avatars → direct save (no crop)
 * - Upload: User picks a file → crop editor → save cropped 1:1 JPEG to custom/
 */
export class AvatarManager {
    constructor(dom) {
        this.dom = dom;
        this.selectedAvatar = null;
        this.selectedAvatarType = null;
        this.creatorMode = false;
        this.userMode = false;        // true = save for user profile instead of persona
        this.onCreatorSave = null;
        
        // Crop state
        this.cropImage = null;         // Image object for crop
        this.cropFile = null;          // Original File object
        this.cropRect = { x: 0, y: 0, size: 0 }; // crop region in image coords
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.scale = 1;                // canvas scale factor
        this.imgOffsetX = 0;
        this.imgOffsetY = 0;
        
        this._setupCropEvents();
    }

    /* ========== OPEN / CLOSE ========== */

    async openAvatarEditor(options = {}) {
        this.creatorMode = !!options.creatorMode;
        this.userMode = !!options.userMode;
        this.onCreatorSave = options.onSave || null;
        
        this.dom.avatarEditorOverlay.classList.remove('hidden');
        this.resetAvatarEditor();
        await this.loadAvatarGallery();
    }

    /**
     * Öffnet den Avatar-Editor im Creator-Modus.
     * @param {Function} callback - Wird mit {avatar, avatar_type} aufgerufen
     */
    async openAvatarEditorForCreator(callback) {
        await this.openAvatarEditor({ creatorMode: true, onSave: callback });
    }

    /**
     * Öffnet den Avatar-Editor für User-Profil
     * @param {Function} callback - Wird mit {avatar, avatar_type} aufgerufen
     */
    async openAvatarEditorForUser(callback) {
        await this.openAvatarEditor({ userMode: true, onSave: callback });
    }

    closeAvatarEditor() {
        this.dom.avatarEditorOverlay.classList.add('hidden');
        this.creatorMode = false;
        this.userMode = false;
        this.onCreatorSave = null;
        this.resetAvatarEditor();
    }
    
    resetAvatarEditor() {
        this.selectedAvatar = null;
        this.selectedAvatarType = null;
        this.cropImage = null;
        this.cropFile = null;
        
        const selStep = document.getElementById('avatar-selection-step');
        const cropStep = document.getElementById('avatar-upload-crop-step');
        if (selStep) { selStep.classList.add('active'); selStep.classList.remove('hidden'); }
        if (cropStep) { cropStep.classList.add('hidden'); cropStep.classList.remove('active'); }
        
        this.dom.avatarBackBtn.classList.add('hidden');
        this.dom.avatarSaveBtn.classList.add('hidden');
    }

    /* ========== GALLERY ========== */
    
    async loadAvatarGallery() {
        try {
            const response = await fetch('/api/get_available_avatars');
            const data = await response.json();
            
            if (data.success) {
                this.dom.avatarGallery.innerHTML = '';
                
                data.avatars.forEach(avatarObj => {
                    const option = document.createElement('div');
                    option.className = 'avatar-option';
                    option.dataset.avatar = avatarObj.filename;
                    option.dataset.type = avatarObj.type;
                    
                    const img = document.createElement('img');
                    const imgPath = avatarObj.type === 'custom' 
                        ? `/static/images/custom/${avatarObj.filename}` 
                        : `/static/images/avatars/${avatarObj.filename}`;
                    img.src = imgPath;
                    img.alt = avatarObj.filename;
                    
                    option.appendChild(img);
                    option.addEventListener('click', () => this.selectAvatar(avatarObj.filename, avatarObj.type));
                    
                    if (avatarObj.type === 'custom') {
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'avatar-option-delete';
                        deleteBtn.innerHTML = '&times;';
                        deleteBtn.addEventListener('click', (e) => {
                            e.stopPropagation();
                            this.deleteCustomAvatar(avatarObj.filename);
                        });
                        option.appendChild(deleteBtn);
                    }
                    
                    this.dom.avatarGallery.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Fehler beim Laden der Avatare:', error);
        }
    }
    
    /**
     * User wählt ein bestehendes Avatar-Bild aus der Gallery.
     * Da alle Bilder bereits 1:1 1024px sind, wird direkt gespeichert.
     */
    async selectAvatar(avatarName, avatarType) {
        this.selectedAvatar = avatarName;
        this.selectedAvatarType = avatarType;
        
        // Highlight in Gallery
        this.dom.avatarGallery.querySelectorAll('.avatar-option').forEach(opt => {
            opt.classList.toggle('selected', opt.dataset.avatar === avatarName);
        });
        
        // Direkt speichern
        await this.saveSelectedAvatar();
    }

    /* ========== SAVE (Gallery Selection) ========== */
    
    async saveSelectedAvatar() {
        if (!this.selectedAvatar) return;
        
        const avatarData = {
            avatar: this.selectedAvatar,
            avatar_type: this.selectedAvatarType || 'standard'
        };
        
        // Creator-Modus: nur Callback, kein Server-Call
        if (this.creatorMode && this.onCreatorSave) {
            this.onCreatorSave(avatarData);
            this.closeAvatarEditor();
            return;
        }
        
        // User-Modus: nur Callback, kein Server-Call  
        if (this.userMode && this.onCreatorSave) {
            this.onCreatorSave(avatarData);
            this.closeAvatarEditor();
            return;
        }
        
        // Normaler Modus: auf dem Server speichern
        try {
            const response = await fetch('/api/save_avatar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...avatarData,
                    target: this.userMode ? 'user' : 'persona'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.location.reload();
            } else {
                alert('Fehler beim Speichern des Avatars: ' + (data.error || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Fehler beim Speichern des Avatars:', error);
            alert('Verbindungsfehler');
        }
    }

    /* ========== UPLOAD + CROP ========== */
    
    openUploadDialog() {
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.value = '';
            fileInput.click();
        }
    }
    
    handleFileSelect(e) {
        const files = e.target?.files || e.dataTransfer?.files;
        if (files && files.length > 0) {
            this.loadImageForCrop(files[0]);
        }
    }
    
    loadImageForCrop(file) {
        if (!file.type.startsWith('image/')) {
            alert('Bitte nur Bilddateien hochladen');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            alert('Datei zu groß (max 10MB)');
            return;
        }
        
        this.cropFile = file;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                this.cropImage = img;
                this._showCropStep();
                this._initCrop();
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
    
    _showCropStep() {
        const selStep = document.getElementById('avatar-selection-step');
        const cropStep = document.getElementById('avatar-upload-crop-step');
        
        if (selStep) { selStep.classList.remove('active'); selStep.classList.add('hidden'); }
        if (cropStep) { cropStep.classList.remove('hidden'); cropStep.classList.add('active'); }
        
        this.dom.avatarBackBtn.classList.remove('hidden');
        this.dom.avatarSaveBtn.classList.remove('hidden');
    }
    
    avatarEditorBack() {
        const selStep = document.getElementById('avatar-selection-step');
        const cropStep = document.getElementById('avatar-upload-crop-step');
        
        if (cropStep) { cropStep.classList.add('hidden'); cropStep.classList.remove('active'); }
        if (selStep) { selStep.classList.remove('hidden'); selStep.classList.add('active'); }
        
        this.dom.avatarBackBtn.classList.add('hidden');
        this.dom.avatarSaveBtn.classList.add('hidden');
        this.cropImage = null;
        this.cropFile = null;
    }
    
    /* ========== CANVAS CROP ========== */
    
    _initCrop() {
        const canvas = document.getElementById('crop-canvas');
        if (!canvas || !this.cropImage) return;
        
        const ctx = canvas.getContext('2d');
        const img = this.cropImage;
        
        // Fit image into canvas
        const canvasSize = 500;
        canvas.width = canvasSize;
        canvas.height = canvasSize;
        
        this.scale = Math.min(canvasSize / img.width, canvasSize / img.height);
        const drawW = img.width * this.scale;
        const drawH = img.height * this.scale;
        this.imgOffsetX = (canvasSize - drawW) / 2;
        this.imgOffsetY = (canvasSize - drawH) / 2;
        
        // Default crop: largest square centered
        const minDim = Math.min(img.width, img.height);
        this.cropRect = {
            x: (img.width - minDim) / 2,
            y: (img.height - minDim) / 2,
            size: minDim
        };
        
        this._drawCrop();
    }
    
    _drawCrop() {
        const canvas = document.getElementById('crop-canvas');
        if (!canvas || !this.cropImage) return;
        
        const ctx = canvas.getContext('2d');
        const img = this.cropImage;
        const canvasSize = canvas.width;
        
        const drawW = img.width * this.scale;
        const drawH = img.height * this.scale;
        
        // Clear
        ctx.clearRect(0, 0, canvasSize, canvasSize);
        
        // Draw image
        ctx.drawImage(img, this.imgOffsetX, this.imgOffsetY, drawW, drawH);
        
        // Draw dark overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, canvasSize, canvasSize);
        
        // Cut out the crop region (show original brightness)
        const cx = this.imgOffsetX + this.cropRect.x * this.scale;
        const cy = this.imgOffsetY + this.cropRect.y * this.scale;
        const cs = this.cropRect.size * this.scale;
        
        ctx.save();
        ctx.beginPath();
        ctx.rect(cx, cy, cs, cs);
        ctx.clip();
        ctx.clearRect(0, 0, canvasSize, canvasSize);
        ctx.drawImage(img, this.imgOffsetX, this.imgOffsetY, drawW, drawH);
        ctx.restore();
        
        // Draw crop border
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.strokeRect(cx, cy, cs, cs);
        
        // Draw corner handles
        const handleSize = 8;
        ctx.fillStyle = '#ffffff';
        // Top-left
        ctx.fillRect(cx - handleSize/2, cy - handleSize/2, handleSize, handleSize);
        // Top-right
        ctx.fillRect(cx + cs - handleSize/2, cy - handleSize/2, handleSize, handleSize);
        // Bottom-left
        ctx.fillRect(cx - handleSize/2, cy + cs - handleSize/2, handleSize, handleSize);
        // Bottom-right
        ctx.fillRect(cx + cs - handleSize/2, cy + cs - handleSize/2, handleSize, handleSize);
        
        // Update preview
        this._drawCropPreview();
    }
    
    _drawCropPreview() {
        const previewCanvas = document.getElementById('crop-preview-canvas');
        if (!previewCanvas || !this.cropImage) return;
        
        const ctx = previewCanvas.getContext('2d');
        const img = this.cropImage;
        const r = this.cropRect;
        
        ctx.clearRect(0, 0, 200, 200);
        
        // Draw circular clip
        ctx.save();
        ctx.beginPath();
        ctx.arc(100, 100, 100, 0, Math.PI * 2);
        ctx.clip();
        
        ctx.drawImage(img, r.x, r.y, r.size, r.size, 0, 0, 200, 200);
        ctx.restore();
        
        // Draw circle border
        ctx.strokeStyle = 'rgba(255,255,255,0.3)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(100, 100, 99, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    _setupCropEvents() {
        // These are set up once, but only act when cropImage is loaded
        document.addEventListener('mousedown', (e) => this._onCropMouseDown(e));
        document.addEventListener('mousemove', (e) => this._onCropMouseMove(e));
        document.addEventListener('mouseup', () => this._onCropMouseUp());
        document.addEventListener('wheel', (e) => this._onCropWheel(e), { passive: false });
        
        // Touch events
        document.addEventListener('touchstart', (e) => this._onCropTouchStart(e), { passive: false });
        document.addEventListener('touchmove', (e) => this._onCropTouchMove(e), { passive: false });
        document.addEventListener('touchend', () => this._onCropMouseUp());
    }
    
    _getCanvasPos(e) {
        const canvas = document.getElementById('crop-canvas');
        if (!canvas) return null;
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    _onCropMouseDown(e) {
        const canvas = document.getElementById('crop-canvas');
        if (!canvas || !this.cropImage) return;
        if (e.target !== canvas) return;
        
        const pos = this._getCanvasPos(e);
        if (!pos) return;
        
        this.isDragging = true;
        this.dragStart = { x: pos.x, y: pos.y };
        this.dragStartRect = { ...this.cropRect };
        e.preventDefault();
    }
    
    _onCropMouseMove(e) {
        if (!this.isDragging || !this.cropImage) return;
        
        const pos = this._getCanvasPos(e);
        if (!pos) return;
        
        const dx = (pos.x - this.dragStart.x) / this.scale;
        const dy = (pos.y - this.dragStart.y) / this.scale;
        
        let newX = this.dragStartRect.x + dx;
        let newY = this.dragStartRect.y + dy;
        
        // Clamp to image bounds
        newX = Math.max(0, Math.min(newX, this.cropImage.width - this.cropRect.size));
        newY = Math.max(0, Math.min(newY, this.cropImage.height - this.cropRect.size));
        
        this.cropRect.x = newX;
        this.cropRect.y = newY;
        
        this._drawCrop();
    }
    
    _onCropMouseUp() {
        this.isDragging = false;
    }
    
    _onCropWheel(e) {
        const canvas = document.getElementById('crop-canvas');
        if (!canvas || !this.cropImage) return;
        if (e.target !== canvas) return;
        
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? 20 : -20; // shrink/grow
        const img = this.cropImage;
        const minSize = Math.min(img.width, img.height, 100);
        const maxSize = Math.min(img.width, img.height);
        
        let newSize = this.cropRect.size + delta;
        newSize = Math.max(minSize, Math.min(newSize, maxSize));
        
        // Adjust position to keep center
        const sizeDiff = newSize - this.cropRect.size;
        let newX = this.cropRect.x - sizeDiff / 2;
        let newY = this.cropRect.y - sizeDiff / 2;
        
        newX = Math.max(0, Math.min(newX, img.width - newSize));
        newY = Math.max(0, Math.min(newY, img.height - newSize));
        
        this.cropRect = { x: newX, y: newY, size: newSize };
        this._drawCrop();
    }
    
    _onCropTouchStart(e) {
        const canvas = document.getElementById('crop-canvas');
        if (!canvas || !this.cropImage) return;
        if (e.target !== canvas) return;
        
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            this._onCropMouseDown({ target: canvas, clientX: touch.clientX, clientY: touch.clientY, preventDefault: () => {} });
            e.preventDefault();
        }
    }
    
    _onCropTouchMove(e) {
        if (!this.isDragging || !this.cropImage) return;
        
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            this._onCropMouseMove({ clientX: touch.clientX, clientY: touch.clientY });
            e.preventDefault();
        }
    }
    
    /* ========== SAVE CROPPED UPLOAD ========== */
    
    async saveCroppedAvatar() {
        if (!this.cropFile || !this.cropImage) return;
        
        this.dom.avatarSaveBtn.disabled = true;
        this.dom.avatarSaveBtn.textContent = 'Speichern...';
        
        const formData = new FormData();
        formData.append('file', this.cropFile);
        formData.append('crop_data', JSON.stringify({
            x: Math.round(this.cropRect.x),
            y: Math.round(this.cropRect.y),
            size: Math.round(this.cropRect.size)
        }));
        
        try {
            const response = await fetch('/api/upload_avatar', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                const avatarData = {
                    avatar: data.filename,
                    avatar_type: 'custom'
                };
                
                // Creator/User Callback mode
                if ((this.creatorMode || this.userMode) && this.onCreatorSave) {
                    this.onCreatorSave(avatarData);
                    this.closeAvatarEditor();
                    return;
                }
                
                // Normal mode: save to persona
                const saveRes = await fetch('/api/save_avatar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ...avatarData,
                        target: this.userMode ? 'user' : 'persona'
                    })
                });
                
                const saveData = await saveRes.json();
                if (saveData.success) {
                    window.location.reload();
                } else {
                    alert('Fehler: ' + (saveData.error || 'Unbekannt'));
                }
            } else {
                alert('Upload-Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Upload-Fehler:', error);
            alert('Verbindungsfehler');
        } finally {
            this.dom.avatarSaveBtn.disabled = false;
            this.dom.avatarSaveBtn.textContent = 'Speichern';
        }
    }

    /* ========== DELETE ========== */

    async deleteCustomAvatar(filename) {
        if (!confirm('Möchtest du dieses Bild wirklich löschen?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/delete_custom_avatar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: filename })
            });
            
            const data = await response.json();
            
            if (data.success) {
                await this.loadAvatarGallery();
            } else {
                alert('Fehler beim Löschen: ' + (data.error || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Fehler beim Löschen des Avatars:', error);
            alert('Verbindungsfehler');
        }
    }
}
