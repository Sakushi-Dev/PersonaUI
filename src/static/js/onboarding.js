/**
 * Onboarding – First-Run Setup für PersonaUI
 * Reine Frontend-Logik, nutzt vorhandene API-Endpunkte.
 * Avatar-Logik: Gallery + Upload + Crop (wie im Chat-Interface)
 */
(function () {
    'use strict';

    const TOTAL_STEPS = 5; // 0-4
    let currentStep = 0;
    let selectedGender = null;
    let selectedInterests = [];
    let darkMode = false;

    // Avatar state
    let selectedAvatar = null;      // filename
    let selectedAvatarType = null;  // 'standard' | 'custom'

    // Crop state
    let cropImage = null;
    let cropFile = null;
    let cropRect = { x: 0, y: 0, size: 0 };
    let isDragging = false;
    let dragStart = { x: 0, y: 0 };
    let dragStartRect = {};
    let cropScale = 1;
    let imgOffsetX = 0;
    let imgOffsetY = 0;

    // ============ DOM Refs ============
    const container = document.getElementById('ob-container');
    const progressFill = document.getElementById('ob-progress-fill');
    const indicators = document.getElementById('ob-step-indicators');

    // ============ INIT ============
    document.addEventListener('DOMContentLoaded', async () => {
        bindEvents();
        bindAvatarEvents();
        bindGenderEvents();
        initApiWarningEvents();
        updateProgress();
    });

    // ============ NAVIGATION ============
    function goTo(step) {
        if (step < 0 || step >= TOTAL_STEPS) return;
        const cur = container.querySelector(`.ob-step.active`);
        if (cur) cur.classList.remove('active');
        const target = container.querySelector(`.ob-step[data-step="${step}"]`);
        if (target) {
            target.classList.remove('active');
            void target.offsetWidth;
            target.classList.add('active');
        }
        currentStep = step;
        updateProgress();
    }

    function updateProgress() {
        const pct = (currentStep / (TOTAL_STEPS - 1)) * 100;
        progressFill.style.width = pct + '%';
        indicators.querySelectorAll('.ob-step-dot').forEach((dot, i) => {
            dot.classList.remove('active', 'completed');
            if (i === currentStep) dot.classList.add('active');
            else if (i < currentStep) dot.classList.add('completed');
        });
    }

    // ============ EVENTS ============
    function bindEvents() {
        // Navigation buttons
        document.getElementById('ob-start-btn')?.addEventListener('click', () => goTo(1));
        document.getElementById('ob-next-1')?.addEventListener('click', () => goTo(2));
        document.getElementById('ob-next-2')?.addEventListener('click', () => goTo(3));
        document.getElementById('ob-next-3')?.addEventListener('click', handleApiStepNext);
        document.getElementById('ob-back-1')?.addEventListener('click', () => goTo(0));
        document.getElementById('ob-back-2')?.addEventListener('click', () => goTo(1));
        document.getElementById('ob-back-3')?.addEventListener('click', () => goTo(2));
        document.getElementById('ob-finish-btn')?.addEventListener('click', finishOnboarding);

        // Step dots
        indicators.querySelectorAll('.ob-step-dot').forEach(dot => {
            dot.addEventListener('click', () => {
                const s = parseInt(dot.dataset.step);
                if (s <= currentStep + 1) goTo(s);
            });
        });

        // User info char counter
        const infoInput = document.getElementById('ob-user-info');
        const infoCount = document.getElementById('ob-info-count');
        infoInput?.addEventListener('input', () => {
            if (infoCount) infoCount.textContent = (infoInput.value || '').length;
        });

        // Name → update avatar placeholder letter
        const nameInput = document.getElementById('ob-user-name');
        nameInput?.addEventListener('input', () => {
            if (!selectedAvatar) {
                const ph = document.getElementById('ob-avatar-placeholder');
                if (ph) ph.textContent = (nameInput.value || 'U').charAt(0).toUpperCase();
            }
        });

        // Dark mode toggle
        const darkToggle = document.getElementById('ob-dark-toggle');
        darkToggle?.addEventListener('change', () => {
            darkMode = darkToggle.checked;
            document.body.classList.toggle('dark-mode', darkMode);
            document.documentElement.classList.toggle('dark-mode-early', darkMode);
            updatePreview();
        });

        // Nonverbal color
        const nvColor = document.getElementById('ob-nonverbal-color');
        const nvColorText = document.getElementById('ob-nonverbal-color-text');
        nvColor?.addEventListener('input', () => {
            if (nvColorText) nvColorText.value = nvColor.value;
            updatePreviewNonverbal(nvColor.value);
        });
        nvColorText?.addEventListener('input', () => {
            const v = nvColorText.value;
            if (/^#[0-9a-fA-F]{6}$/.test(v)) {
                nvColor.value = v;
                updatePreviewNonverbal(v);
            }
        });

        // Context limit slider
        const ctxSlider = document.getElementById('ob-context-limit');
        const ctxDisplay = document.getElementById('ob-context-display');
        ctxSlider?.addEventListener('input', () => {
            if (ctxDisplay) ctxDisplay.textContent = ctxSlider.value;
        });

        // API key eye toggle
        const eyeBtn = document.getElementById('ob-api-eye');
        const apiKeyInput = document.getElementById('ob-api-key');
        eyeBtn?.addEventListener('click', () => {
            if (apiKeyInput) {
                apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
            }
        });

        // Test API key
        document.getElementById('ob-test-api-btn')?.addEventListener('click', testApiKey);

        // Paste API key
        document.getElementById('ob-api-paste')?.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && apiKeyInput) {
                    apiKeyInput.value = text.trim();
                    apiKeyInput.type = 'text';
                    setTimeout(() => { apiKeyInput.type = 'password'; }, 1500);
                }
            } catch (e) {
                // Clipboard access denied
            }
        });
    }

    // ============================================================
    //  AVATAR – Gallery, Upload, Crop (selbe Logik wie AvatarManager)
    // ============================================================

    function bindAvatarEvents() {
        // Click avatar circle → open gallery overlay
        document.getElementById('ob-avatar-upload')?.addEventListener('click', openAvatarGallery);

        // Close gallery
        document.getElementById('ob-avatar-gallery-close')?.addEventListener('click', closeAvatarGallery);

        // Click backdrop → close
        document.getElementById('ob-avatar-gallery-overlay')?.addEventListener('click', (e) => {
            if (e.target.id === 'ob-avatar-gallery-overlay') closeAvatarGallery();
        });

        // Remove avatar
        document.getElementById('ob-avatar-remove-btn')?.addEventListener('click', removeAvatar);

        // Drop zone click → file input
        const dropzone = document.getElementById('ob-avatar-dropzone');
        const fileInput = document.getElementById('ob-avatar-file');
        dropzone?.addEventListener('click', () => fileInput?.click());
        fileInput?.addEventListener('change', (e) => handleFileSelect(e.target.files));

        // Drop zone drag & drop
        dropzone?.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
        dropzone?.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
        dropzone?.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            handleFileSelect(e.dataTransfer.files);
        });

        // Crop: back / save
        document.getElementById('ob-crop-back')?.addEventListener('click', showGalleryStep);
        document.getElementById('ob-crop-save')?.addEventListener('click', saveCroppedAvatar);

        // Crop: mouse/touch/wheel events
        document.addEventListener('mousedown', onCropMouseDown);
        document.addEventListener('mousemove', onCropMouseMove);
        document.addEventListener('mouseup', () => { isDragging = false; });
        document.addEventListener('wheel', onCropWheel, { passive: false });
        document.addEventListener('touchstart', onCropTouchStart, { passive: false });
        document.addEventListener('touchmove', onCropTouchMove, { passive: false });
        document.addEventListener('touchend', () => { isDragging = false; });
    }

    // ---- Gallery ----
    async function openAvatarGallery() {
        const overlay = document.getElementById('ob-avatar-gallery-overlay');
        overlay?.classList.remove('hidden');
        showGalleryStep();
        await loadAvatarGallery();
    }

    function closeAvatarGallery() {
        document.getElementById('ob-avatar-gallery-overlay')?.classList.add('hidden');
        cropImage = null;
        cropFile = null;
    }

    async function loadAvatarGallery() {
        try {
            const res = await fetch('/api/get_available_avatars');
            const data = await res.json();
            if (!data.success) return;

            const grid = document.getElementById('ob-avatar-grid');
            if (!grid) return;
            grid.innerHTML = '';

            data.avatars.forEach(avatarObj => {
                const option = document.createElement('div');
                option.className = 'ob-avatar-option';
                if (selectedAvatar === avatarObj.filename) option.classList.add('selected');

                const img = document.createElement('img');
                const imgPath = avatarObj.type === 'custom'
                    ? `/static/images/custom/${avatarObj.filename}`
                    : `/static/images/avatars/${avatarObj.filename}`;
                img.src = imgPath;
                img.alt = avatarObj.filename;
                img.loading = 'lazy';
                option.appendChild(img);

                option.addEventListener('click', () => selectGalleryAvatar(avatarObj.filename, avatarObj.type));
                grid.appendChild(option);
            });
        } catch (e) {
            console.error('Fehler beim Laden der Avatare:', e);
        }
    }

    function selectGalleryAvatar(filename, type) {
        selectedAvatar = filename;
        selectedAvatarType = type;
        updateAvatarPreview();
        closeAvatarGallery();
    }

    function removeAvatar() {
        selectedAvatar = null;
        selectedAvatarType = null;
        updateAvatarPreview();
    }

    function updateAvatarPreview() {
        const upload = document.getElementById('ob-avatar-upload');
        const placeholder = document.getElementById('ob-avatar-placeholder');
        const removeBtn = document.getElementById('ob-avatar-remove-btn');

        if (selectedAvatar) {
            const path = selectedAvatarType === 'custom'
                ? `/static/images/custom/${selectedAvatar}`
                : `/static/images/avatars/${selectedAvatar}`;
            upload.style.backgroundImage = `url('${path}')`;
            upload.style.backgroundSize = 'cover';
            upload.style.backgroundPosition = 'center';
            upload.classList.add('has-avatar');
            if (placeholder) placeholder.style.display = 'none';
            removeBtn?.classList.remove('hidden');
        } else {
            upload.style.backgroundImage = '';
            upload.classList.remove('has-avatar');
            if (placeholder) {
                placeholder.style.display = '';
                const name = document.getElementById('ob-user-name')?.value || 'User';
                placeholder.textContent = name.charAt(0).toUpperCase();
            }
            removeBtn?.classList.add('hidden');
        }
    }

    // ---- Upload + Crop ----
    function handleFileSelect(files) {
        if (!files || !files.length) return;
        const file = files[0];
        if (!file.type.startsWith('image/')) return;
        if (file.size > 10 * 1024 * 1024) { alert('Datei zu groß (max 10MB)'); return; }

        cropFile = file;
        const reader = new FileReader();
        reader.onload = (ev) => {
            const img = new Image();
            img.onload = () => {
                cropImage = img;
                showCropStep();
                initCrop();
            };
            img.src = ev.target.result;
        };
        reader.readAsDataURL(file);
    }

    function showGalleryStep() {
        document.getElementById('ob-avatar-select-step')?.classList.remove('hidden');
        document.getElementById('ob-avatar-select-step')?.classList.add('active');
        document.getElementById('ob-avatar-crop-step')?.classList.add('hidden');
        document.getElementById('ob-avatar-crop-step')?.classList.remove('active');
        cropImage = null;
        cropFile = null;
    }

    function showCropStep() {
        document.getElementById('ob-avatar-select-step')?.classList.add('hidden');
        document.getElementById('ob-avatar-select-step')?.classList.remove('active');
        document.getElementById('ob-avatar-crop-step')?.classList.remove('hidden');
        document.getElementById('ob-avatar-crop-step')?.classList.add('active');
    }

    function initCrop() {
        const canvas = document.getElementById('ob-crop-canvas');
        if (!canvas || !cropImage) return;

        const canvasSize = 400;
        canvas.width = canvasSize;
        canvas.height = canvasSize;

        cropScale = Math.min(canvasSize / cropImage.width, canvasSize / cropImage.height);
        const drawW = cropImage.width * cropScale;
        const drawH = cropImage.height * cropScale;
        imgOffsetX = (canvasSize - drawW) / 2;
        imgOffsetY = (canvasSize - drawH) / 2;

        const minDim = Math.min(cropImage.width, cropImage.height);
        cropRect = {
            x: (cropImage.width - minDim) / 2,
            y: (cropImage.height - minDim) / 2,
            size: minDim
        };
        drawCrop();
    }

    function drawCrop() {
        const canvas = document.getElementById('ob-crop-canvas');
        if (!canvas || !cropImage) return;
        const ctx = canvas.getContext('2d');
        const img = cropImage;
        const canvasSize = canvas.width;
        const drawW = img.width * cropScale;
        const drawH = img.height * cropScale;

        ctx.clearRect(0, 0, canvasSize, canvasSize);
        ctx.drawImage(img, imgOffsetX, imgOffsetY, drawW, drawH);

        // Dark overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, canvasSize, canvasSize);

        // Crop window
        const cx = imgOffsetX + cropRect.x * cropScale;
        const cy = imgOffsetY + cropRect.y * cropScale;
        const cs = cropRect.size * cropScale;

        ctx.save();
        ctx.beginPath();
        ctx.rect(cx, cy, cs, cs);
        ctx.clip();
        ctx.clearRect(0, 0, canvasSize, canvasSize);
        ctx.drawImage(img, imgOffsetX, imgOffsetY, drawW, drawH);
        ctx.restore();

        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.strokeRect(cx, cy, cs, cs);

        // Corner handles
        const hs = 8;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(cx - hs/2, cy - hs/2, hs, hs);
        ctx.fillRect(cx + cs - hs/2, cy - hs/2, hs, hs);
        ctx.fillRect(cx - hs/2, cy + cs - hs/2, hs, hs);
        ctx.fillRect(cx + cs - hs/2, cy + cs - hs/2, hs, hs);

        drawCropPreview();
    }

    function drawCropPreview() {
        const preview = document.getElementById('ob-crop-preview');
        if (!preview || !cropImage) return;
        const ctx = preview.getContext('2d');
        const r = cropRect;

        ctx.clearRect(0, 0, 160, 160);
        ctx.save();
        ctx.beginPath();
        ctx.arc(80, 80, 80, 0, Math.PI * 2);
        ctx.clip();
        ctx.drawImage(cropImage, r.x, r.y, r.size, r.size, 0, 0, 160, 160);
        ctx.restore();

        ctx.strokeStyle = 'rgba(255,255,255,0.3)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(80, 80, 79, 0, Math.PI * 2);
        ctx.stroke();
    }

    // Crop interaction
    function getCanvasPos(e) {
        const canvas = document.getElementById('ob-crop-canvas');
        if (!canvas) return null;
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
    }

    function onCropMouseDown(e) {
        const canvas = document.getElementById('ob-crop-canvas');
        if (!canvas || !cropImage || e.target !== canvas) return;
        const pos = getCanvasPos(e);
        if (!pos) return;
        isDragging = true;
        dragStart = { x: pos.x, y: pos.y };
        dragStartRect = { ...cropRect };
        e.preventDefault();
    }

    function onCropMouseMove(e) {
        if (!isDragging || !cropImage) return;
        const pos = getCanvasPos(e);
        if (!pos) return;
        const dx = (pos.x - dragStart.x) / cropScale;
        const dy = (pos.y - dragStart.y) / cropScale;
        cropRect.x = Math.max(0, Math.min(dragStartRect.x + dx, cropImage.width - cropRect.size));
        cropRect.y = Math.max(0, Math.min(dragStartRect.y + dy, cropImage.height - cropRect.size));
        drawCrop();
    }

    function onCropWheel(e) {
        const canvas = document.getElementById('ob-crop-canvas');
        if (!canvas || !cropImage || e.target !== canvas) return;
        e.preventDefault();
        const delta = e.deltaY > 0 ? 20 : -20;
        const minSize = Math.min(cropImage.width, cropImage.height, 80);
        const maxSize = Math.min(cropImage.width, cropImage.height);
        let newSize = Math.max(minSize, Math.min(cropRect.size + delta, maxSize));
        const diff = newSize - cropRect.size;
        cropRect.x = Math.max(0, Math.min(cropRect.x - diff / 2, cropImage.width - newSize));
        cropRect.y = Math.max(0, Math.min(cropRect.y - diff / 2, cropImage.height - newSize));
        cropRect.size = newSize;
        drawCrop();
    }

    function onCropTouchStart(e) {
        const canvas = document.getElementById('ob-crop-canvas');
        if (!canvas || !cropImage || e.target !== canvas) return;
        if (e.touches.length === 1) {
            const t = e.touches[0];
            onCropMouseDown({ target: canvas, clientX: t.clientX, clientY: t.clientY, preventDefault: () => {} });
            e.preventDefault();
        }
    }

    function onCropTouchMove(e) {
        if (!isDragging || !cropImage) return;
        if (e.touches.length === 1) {
            onCropMouseMove({ clientX: e.touches[0].clientX, clientY: e.touches[0].clientY });
            e.preventDefault();
        }
    }

    async function saveCroppedAvatar() {
        if (!cropFile || !cropImage) return;
        const saveBtn = document.getElementById('ob-crop-save');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Speichern...'; }

        const formData = new FormData();
        formData.append('file', cropFile);
        formData.append('crop_data', JSON.stringify({
            x: Math.round(cropRect.x),
            y: Math.round(cropRect.y),
            size: Math.round(cropRect.size)
        }));

        try {
            const res = await fetch('/api/upload_avatar', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success) {
                selectedAvatar = data.filename;
                selectedAvatarType = 'custom';
                updateAvatarPreview();
                closeAvatarGallery();
            } else {
                alert('Upload-Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (e) {
            console.error('Upload-Fehler:', e);
            alert('Verbindungsfehler');
        } finally {
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Speichern'; }
        }
    }

    // ============ GENDER / INTERESTED IN ============
    function bindGenderEvents() {
        // Geschlecht (Single Select)
        document.querySelectorAll('#ob-gender-grid .ob-type-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const gender = chip.dataset.gender;
                if (selectedGender === gender) {
                    selectedGender = null;
                    chip.classList.remove('active');
                } else {
                    document.querySelectorAll('#ob-gender-grid .ob-type-chip').forEach(c => c.classList.remove('active'));
                    selectedGender = gender;
                    chip.classList.add('active');
                }
            });
        });

        // Interessiere mich für (Multi Select)
        document.querySelectorAll('#ob-interested-grid .ob-type-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const interest = chip.dataset.interest;
                const idx = selectedInterests.indexOf(interest);
                if (idx >= 0) {
                    selectedInterests.splice(idx, 1);
                    chip.classList.remove('active');
                } else {
                    selectedInterests.push(interest);
                    chip.classList.add('active');
                    // Nudge: scroll zum "Über mich" Feld
                    nudgeUserInfo();
                }
            });
        });
    }

    let nudgeFired = false;

    function nudgeUserInfo() {
        if (nudgeFired) return;
        nudgeFired = true;

        const infoField = document.getElementById('ob-user-info');
        if (!infoField) { nudgeFired = false; return; }
        const fieldGroup = infoField.closest('.ob-field-group');
        if (!fieldGroup) { nudgeFired = false; return; }

        // Sanft zum Feld scrollen (innerhalb .ob-card-body)
        fieldGroup.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Highlight-Effekt
        fieldGroup.classList.add('ob-nudge');
        setTimeout(() => {
            fieldGroup.classList.remove('ob-nudge');
            // 5 Sekunden Pause bevor erneut getriggert werden kann
            setTimeout(() => { nudgeFired = false; }, 5000);
        }, 900);
    }

    // ============ PREVIEW ============
    function updatePreview() {
        const bg = document.getElementById('ob-preview-bg');
        const blob1 = document.getElementById('ob-prev-blob-1');
        const blob2 = document.getElementById('ob-prev-blob-2');
        if (darkMode) {
            if (bg) bg.style.background = '#1a2332';
            if (blob1) blob1.style.background = '#2a3f5f';
            if (blob2) blob2.style.background = '#3d4f66';
        } else {
            if (bg) bg.style.background = '#a3baff';
            if (blob1) blob1.style.background = '#66cfff';
            if (blob2) blob2.style.background = '#fd91ee';
        }
    }

    function updatePreviewNonverbal(color) {
        const el = document.getElementById('ob-preview-nonverbal');
        if (el) el.style.color = color;
    }

    // ============ API KEY TEST ============
    async function testApiKey() {
        const input = document.getElementById('ob-api-key');
        const key = input?.value?.trim();
        if (!key) { showApiStatus('Bitte API-Key eingeben', 'error'); return; }

        showApiStatus('Teste API-Key...', 'loading');
        try {
            const res = await fetch('/api/test_api_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key })
            });
            const data = await res.json();
            showApiStatus(data.success ? '✓ API-Key ist gültig!' : '✗ ' + (data.error || 'API-Key ungültig'), data.success ? 'success' : 'error');
            apiKeyValid = !!data.success;
        } catch (e) {
            showApiStatus('✗ Verbindungsfehler', 'error');
        }
    }

    function showApiStatus(msg, type) {
        const el = document.getElementById('ob-api-status');
        if (!el) return;
        el.textContent = msg;
        el.className = 'ob-api-status ' + type;
    }

    // ============ API WARNING ============
    var apiKeyValid = false;

    function handleApiStepNext() {
        if (apiKeyValid) {
            goTo(4);
            return;
        }
        // Show warning overlay
        var overlay = document.getElementById('ob-api-warning-overlay');
        if (overlay) overlay.classList.remove('hidden');
    }

    function initApiWarningEvents() {
        document.getElementById('ob-api-warning-back')?.addEventListener('click', function() {
            document.getElementById('ob-api-warning-overlay')?.classList.add('hidden');
            document.getElementById('ob-api-key')?.focus();
        });
        document.getElementById('ob-api-warning-continue')?.addEventListener('click', function() {
            document.getElementById('ob-api-warning-overlay')?.classList.add('hidden');
            showExploreFinish();
            goTo(4);
        });
        // Close on overlay background click
        document.getElementById('ob-api-warning-overlay')?.addEventListener('click', function(e) {
            if (e.target === this) this.classList.add('hidden');
        });

        // Explore finish button
        document.getElementById('ob-finish-btn-explore')?.addEventListener('click', finishOnboarding);
    }

    function showExploreFinish() {
        document.getElementById('ob-finish-with-api')?.classList.add('hidden');
        document.getElementById('ob-finish-no-api')?.classList.remove('hidden');
    }

    // ============ FINISH / SAVE ============
    async function finishOnboarding() {
        const btn = document.getElementById('ob-finish-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = 'Speichere... <span class="ob-btn-arrow">⏳</span>';
        }

        try {
            // 1) Save user profile (inkl. Avatar aus Gallery-Auswahl)
            const profileData = {
                user_name: document.getElementById('ob-user-name')?.value?.trim() || 'User',
                user_gender: selectedGender || null,
                user_interested_in: selectedInterests.length > 0 ? selectedInterests : [],
                user_info: document.getElementById('ob-user-info')?.value?.trim() || '',
                user_avatar: selectedAvatar || null,
                user_avatar_type: selectedAvatarType || null
            };
            await fetch('/api/user-profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(profileData)
            });

            // 2) Save settings
            const settingsData = {
                darkMode: darkMode,
                nonverbalColor: document.getElementById('ob-nonverbal-color')?.value || '#e4ba00',
                contextLimit: document.getElementById('ob-context-limit')?.value || '65',
                nachgedankeEnabled: document.getElementById('ob-nachgedanke-toggle')?.checked || false
            };
            await fetch('/api/user-settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settingsData)
            });

            // 3) Save API key if provided
            const apiKey = document.getElementById('ob-api-key')?.value?.trim();
            if (apiKey) {
                await fetch('/api/save_api_key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey })
                });
            }

            // 4) Sync dark mode to localStorage for chat.html
            localStorage.setItem('darkMode', darkMode ? 'true' : 'false');

            // 5) Mark onboarding complete
            await fetch('/api/onboarding/complete', { method: 'POST' });

            // 6) Redirect to main app
            window.location.href = '/';

        } catch (e) {
            console.error('Fehler beim Speichern:', e);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'PersonaUI starten <span class="ob-btn-arrow">→</span>';
            }
        }
    }

})();
