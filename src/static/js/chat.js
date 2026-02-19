/**
 * Main Chat Application - Modular Version
 * Coordinates all managers and handles initialization
 */

import { DOMManager } from './modules/DOMManager.js';
import { SettingsManager } from './modules/SettingsManager.js';
import { SessionManager } from './modules/SessionManager.js';
import { MessageManager } from './modules/MessageManager.js';
import { AvatarManager } from './modules/AvatarManager.js';
import { MemoryManager } from './modules/MemoryManager.js';
import { QRCodeManager } from './modules/QRCodeManager.js';
import { UserSettings } from './modules/UserSettings.js';
import { CustomSpecsManager } from './modules/CustomSpecsManager.js';
import { AccessControlManager } from './modules/AccessControlManager.js';
import { UserProfileManager } from './modules/UserProfileManager.js';
import { DebugPanel } from './modules/DebugPanel.js';

class ChatApp {
    constructor() {
        // Initialize all managers
        this.dom = new DOMManager();
        this.settings = new SettingsManager(this.dom);
        this.sessions = new SessionManager(this.dom);
        this.messages = new MessageManager(this.dom);
        window.messageManager = this.messages; // Global für SettingsManager Zugriff
        this.avatar = new AvatarManager(this.dom);
        this.memory = new MemoryManager();
        this.qrCode = new QRCodeManager();
        this.customSpecs = new CustomSpecsManager(this.dom);
        this.accessControl = new AccessControlManager(this.dom);
        this.userProfile = new UserProfileManager(this.dom, this.avatar);
        this.debugPanel = new DebugPanel(this.memory);
        window._accessControl = this.accessControl; // Global für Inline-Onclick-Handler
        
        // Share customSpecs with settings for highlighting + refresh
        this.settings.customSpecs = this.customSpecs;
        this.customSpecs.settingsManager = this.settings;
        
        // Share SessionManager with SettingsManager for sidebar refresh after persona save
        this.settings.sessionManager = this.sessions;
        
        // Share MessageManager with SettingsManager for afterthought timer control
        this.settings.messageManager = this.messages;
        
        // Share MessageManager und MemoryManager mit SessionManager für Soft-Reload
        this.sessions.messageManager = this.messages;
        this.sessions.memoryManager = this.memory;
        
        // Set message sent callback für Memory
        this.messages.setMessageSentCallback(() => this.memory.onMessageSent());
        
        // Initialize
        this.init();
    }
    
    async init() {
        // Settings vom Server laden (muss vor allem anderen passieren)
        await UserSettings.load();
        
        this.setupEventListeners();
        this.setupOverlayWatcher();
        await this.sessions.init(); // Async: loads personas and renders sidebar
        this.settings.loadSavedSettings();
        this.messages.processExistingMessages();
        this.messages.observePersonaNameChanges();
        this.messages.updateLoadMoreButton();
        this.messages.updateNewChatButtonState();
        this.sessions.updateDeleteButtonStates();
        this.settings.checkApiStatus();
        this.messages.autoResize();
        this.messages.scrollToBottom(true);
        this.initModeToggle();
        this.initSoundToggle();
        
        // Zugangskontrolle: Polling starten (prüft intern ob Listen-Modus aktiv ist)
        this.initAccessControl();
        
        // Setze Focus auf das Message-Input-Feld
        setTimeout(() => {
            this.dom.messageInput.focus();
        }, 100);
    }
    
    async initAccessControl() {
        try {
            const response = await fetch('/api/get_server_settings');
            const data = await response.json();
            if (data.success && data.server_mode === 'listen') {
                this.accessControl.startPolling();
            }
        } catch (error) {
            // Im lokalen Modus ist Polling nicht nötig
        }
    }
    
    setupEventListeners() {
        // Message input events
        this.dom.sendButton.addEventListener('click', () => {
            this.messages.sendMessage();
        });
        
        this.dom.messageInput.addEventListener('keydown', (e) => {
            this.messages.handleKeyPress(e);
        });
        
        this.dom.messageInput.addEventListener('input', () => {
            this.messages.autoResize();
        });
        
        // Sidebar events
        this.dom.sidebarToggle.addEventListener('click', () => {
            this.sessions.toggleSidebar();
        });
        
        // Header-Avatar & Character-Name Klick → Sidebar im Persona-Kontakte-Fenster öffnen
        const characterInfo = document.querySelector('.character-info');
        if (characterInfo) {
            characterInfo.style.cursor = 'pointer';
            characterInfo.addEventListener('click', (e) => {
                e.stopPropagation();
                this.sessions.showPersonasView();
                this.sessions.openSidebar();
            });
        }
        
        // Sidebar Zurück-Button (Sessions → Personas)
        this.dom.sidebarBackBtn.addEventListener('click', () => {
            this.sessions.goBackToPersonas();
        });
        
        // ===== SIDEBAR EDGE ACTIVATION ZONE =====
        this._setupEdgeActivation();
        
        // ===== MOBILE SWIPE SUPPORT =====
        this._setupMobileSwipe();
        
        this.dom.newChatBtn.addEventListener('click', () => {
            this.sessions.createNewSession();
        });

        // Welcome-Screen Button
        const welcomeStartBtn = document.getElementById('welcome-start-btn');
        if (welcomeStartBtn) {
            welcomeStartBtn.addEventListener('click', () => {
                this.sessions.createNewSession();
            });
        }
        
        // Session list events
        this.dom.sessionsList.addEventListener('click', (e) => {
            const sessionItem = e.target.closest('.session-item');
            const deleteBtn = e.target.closest('.session-delete');
            
            if (deleteBtn) {
                e.stopPropagation();
                const sessionId = parseInt(deleteBtn.dataset.sessionId);
                this.sessions.deleteSession(sessionId);
            } else if (sessionItem) {
                const sessionId = parseInt(sessionItem.dataset.sessionId);
                this.sessions.loadSession(sessionId);
                // Informiere Memory-Manager über Session-Wechsel
                this.memory.onSessionChange();
            }
        });
        
        // Settings dropdown
        this.dom.settingsDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
            this.settings.toggleDropdown();
        });
        
        // Settings submenu toggle (Einstellungen → Persona/Interface/KI-Modell)
        const submenuToggle = document.getElementById('settings-submenu-toggle');
        const submenu = document.getElementById('settings-submenu');
        if (submenuToggle && submenu) {
            submenuToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                submenuToggle.classList.toggle('open');
                submenu.classList.toggle('open');
            });
        }
        
        document.addEventListener('click', (e) => {
            if (!this.dom.settingsDropdown.contains(e.target)) {
                this.settings.closeDropdown();
                // Submenu auch schließen wenn Dropdown geschlossen wird
                if (submenuToggle) submenuToggle.classList.remove('open');
                if (submenu) submenu.classList.remove('open');
            }
            
            // Sidebar automatisch einklappen, wenn außerhalb geklickt wird
            if (!this.sessions.sidebarCollapsed && 
                !this.dom.sidebar.contains(e.target) &&
                !this.dom.sidebarEdgeZone.contains(e.target)) {
                this.sessions.closeSidebar();
            }
        });
        
        // Character settings
        this.dom.editCharacterBtn.addEventListener('click', () => {
            this.settings.closeDropdown();
            this.settings.openCharacterSettings();
        });
        
        this.dom.closeSettingsBtn.addEventListener('click', () => {
            this.settings.closeCharacterSettings();
        });
        
        this.dom.saveCharacterBtn.addEventListener('click', () => {
            this.settings.saveCharacterSettings();
        });
        
        this.dom.resetCharacterBtn.addEventListener('click', () => {
            this.settings.resetCharacterSettings();
        });
        
        // Persona list/creator navigation
        this.dom.openPersonaCreatorBtn.addEventListener('click', () => {
            this.settings.showPersonaCreator();
        });
        
        this.dom.backToPersonaListBtn.addEventListener('click', () => {
            this.settings.showPersonaList();
            this.settings.renderPersonaGrid();
        });
        
        // Custom Specs
        if (this.dom.openCustomSpecsBtn) {
            this.dom.openCustomSpecsBtn.addEventListener('click', () => {
                this.customSpecs.openCustomSpecs();
            });
        }
        if (this.dom.closeCustomSpecsBtn) {
            this.dom.closeCustomSpecsBtn.addEventListener('click', () => {
                this.customSpecs.closeCustomSpecs();
            });
        }
        
        // API Key Warning Overlay
        const closeApiWarningBtn = document.getElementById('close-api-warning');
        const closeApiWarningBtn2 = document.getElementById('close-api-warning-btn');
        const openApiSettingsBtn = document.getElementById('open-api-settings-btn');
        
        if (closeApiWarningBtn) {
            closeApiWarningBtn.addEventListener('click', () => {
                const overlay = document.getElementById('api-key-warning-overlay');
                if (overlay) overlay.classList.add('hidden');
                // Setze Focus zurück auf Message-Input
                this.dom.messageInput.focus();
            });
        }
        
        if (closeApiWarningBtn2) {
            closeApiWarningBtn2.addEventListener('click', () => {
                const overlay = document.getElementById('api-key-warning-overlay');
                if (overlay) overlay.classList.add('hidden');
                // Setze Focus zurück auf Message-Input
                this.dom.messageInput.focus();
            });
        }
        
        if (openApiSettingsBtn) {
            openApiSettingsBtn.addEventListener('click', () => {
                const overlay = document.getElementById('api-key-warning-overlay');
                if (overlay) overlay.classList.add('hidden');
                this.settings.openApiKeySettings();
            });
        }
        
        // Credit Exhausted Overlay
        const closeCreditWarning = document.getElementById('close-credit-warning');
        const closeCreditWarningBtn = document.getElementById('close-credit-warning-btn');
        
        if (closeCreditWarning) {
            closeCreditWarning.addEventListener('click', () => {
                const overlay = document.getElementById('credit-exhausted-overlay');
                if (overlay) overlay.classList.add('hidden');
                this.dom.messageInput.focus();
            });
        }
        
        if (closeCreditWarningBtn) {
            closeCreditWarningBtn.addEventListener('click', () => {
                const overlay = document.getElementById('credit-exhausted-overlay');
                if (overlay) overlay.classList.add('hidden');
                this.dom.messageInput.focus();
            });
        }
        
        // API Key settings
        this.dom.apiKeyBtn.addEventListener('click', () => {
            this.settings.closeDropdown();
            this.settings.openApiKeySettings();
        });
        
        this.dom.closeApiKeyBtn.addEventListener('click', () => {
            this.settings.closeApiKeySettings();
        });
        
        this.dom.testApiKeyBtn.addEventListener('click', () => {
            this.settings.testApiKey();
        });
        
        this.dom.saveApiKeyBtn.addEventListener('click', () => {
            this.settings.saveApiKey();
        });

        this.dom.pasteApiKeyBtn?.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text && this.dom.apiKeyInput) {
                    this.dom.apiKeyInput.value = text.trim();
                    this.dom.apiKeyInput.type = 'text';
                    setTimeout(() => { this.dom.apiKeyInput.type = 'password'; }, 1500);
                }
            } catch (e) {
                // Clipboard access denied
            }
        });
        
        // Interface settings
        this.dom.interfaceSettingsBtn.addEventListener('click', () => {
            this.settings.closeDropdown();
            this.settings.openInterfaceSettings();
        });
        
        this.dom.closeInterfaceSettingsBtn.addEventListener('click', () => {
            this.settings.closeInterfaceSettings();
        });
        
        this.dom.saveInterfaceBtn.addEventListener('click', () => {
            this.settings.saveInterfaceSettings();
        });
        
        this.dom.resetInterfaceBtn.addEventListener('click', () => {
            this.settings.resetInterfaceSettings();
        });
        
        // API settings
        this.dom.apiSettingsBtn.addEventListener('click', () => {
            this.settings.closeDropdown();
            this.settings.openApiSettings();
        });
        
        this.dom.closeApiSettingsBtn.addEventListener('click', () => {
            this.settings.closeApiSettings();
        });
        
        this.dom.saveApiSettingsBtn.addEventListener('click', () => {
            this.settings.saveApiSettings();
        });
        
        this.dom.resetApiSettingsBtn.addEventListener('click', () => {
            this.settings.resetApiSettings();
        });
        
        // Server settings
        this.dom.serverSettingsBtn.addEventListener('click', () => {
            this.settings.closeDropdown();
            this.settings.openServerSettings();
        });
        
        this.dom.closeServerSettingsBtn.addEventListener('click', () => {
            this.settings.closeServerSettings();
        });
        
        this.dom.closeServerSettingsCancelBtn.addEventListener('click', () => {
            this.settings.closeServerSettings();
        });
        
        this.dom.saveServerSettingsBtn.addEventListener('click', () => {
            this.settings.saveServerSettings();
        });
        
        // Access Control overlay
        const accessControlBtn = document.getElementById('access-control-btn');
        if (accessControlBtn) {
            accessControlBtn.addEventListener('click', () => {
                this.settings.closeDropdown();
                this.accessControl.openOverlay();
            });
        }
        
        // User Profile overlay
        if (this.dom.userProfileBtn) {
            this.dom.userProfileBtn.addEventListener('click', () => {
                this.settings.closeDropdown();
                this.userProfile.open();
            });
        }
        this.userProfile.setupEventListeners();
        
        // Avatar editor (now triggered from creator area only, in creator mode)
        this.dom.creatorChangeAvatarBtn.addEventListener('click', () => {
            this.avatar.openAvatarEditorForCreator((avatarData) => {
                this.settings.setCreatorAvatar(avatarData);
            });
        });
        
        this.dom.closeAvatarEditorBtn.addEventListener('click', () => {
            this.avatar.closeAvatarEditor();
        });
        
        this.dom.avatarBackBtn.addEventListener('click', () => {
            this.avatar.avatarEditorBack();
        });
        
        this.dom.avatarSaveBtn.addEventListener('click', () => {
            this.avatar.saveCroppedAvatar();
        });
        
        // Drop zone → click opens file dialog
        this.dom.avatarDropZone.addEventListener('click', () => {
            this.avatar.openUploadDialog();
        });

        // Drop zone → drag & drop
        this.dom.avatarDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dom.avatarDropZone.classList.add('drag-over');
        });
        this.dom.avatarDropZone.addEventListener('dragleave', () => {
            this.dom.avatarDropZone.classList.remove('drag-over');
        });
        this.dom.avatarDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dom.avatarDropZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) this.avatar.loadImageForCrop(file);
        });
        
        this.dom.fileInput.addEventListener('change', (e) => {
            this.avatar.handleFileSelect(e);
        });
        
        // Close overlays when clicking outside
        this.dom.characterOverlay.addEventListener('click', (e) => {
            if (e.target === this.dom.characterOverlay) {
                this.settings.closeCharacterSettings();
            }
        });
        
        this.dom.apiKeyOverlay.addEventListener('click', (e) => {
            if (e.target === this.dom.apiKeyOverlay) {
                this.settings.closeApiKeySettings();
            }
        });
        
        this.dom.interfaceSettingsOverlay.addEventListener('click', (e) => {
            if (e.target === this.dom.interfaceSettingsOverlay) {
                this.settings.closeInterfaceSettings();
            }
        });
        
        this.dom.avatarEditorOverlay.addEventListener('click', (e) => {
            if (e.target === this.dom.avatarEditorOverlay) {
                this.avatar.closeAvatarEditor();
            }
        });
    }
    
    initModeToggle() {
        const toggle = document.getElementById('mode-toggle');
        if (!toggle) return;
        
        // Lade gespeicherten Zustand (Standard: false / Default)
        const saved = UserSettings.get('experimentalMode', false);
        toggle.checked = saved;
        this.updateModeLabels(saved);
        
        // Event Listener
        toggle.addEventListener('change', () => {
            const isExperimental = toggle.checked;
            UserSettings.set('experimentalMode', isExperimental);
            this.updateModeLabels(isExperimental);
        });
    }
    
    updateModeLabels(isExperimental) {
        const defaultLabel = document.querySelector('.mode-toggle-container .default-label');
        const experimentalLabel = document.querySelector('.mode-toggle-container .experimental-label-text');
        if (defaultLabel) defaultLabel.classList.toggle('active', !isExperimental);
        if (experimentalLabel) experimentalLabel.classList.toggle('active', isExperimental);
    }

    initSoundToggle() {
        const btn = document.getElementById('sound-toggle-btn');
        if (!btn) return;
        
        const enabled = UserSettings.get('notificationSound', true);
        this._updateSoundButton(btn, enabled);
        
        btn.addEventListener('click', () => {
            const newState = !this.messages.notificationSoundEnabled;
            this.messages.setNotificationSound(newState);
            this._updateSoundButton(btn, newState);
        });
    }
    
    _updateSoundButton(btn, enabled) {
        const onIcon = btn.querySelector('.sound-on');
        const offIcon = btn.querySelector('.sound-off');
        btn.classList.toggle('muted', !enabled);
        btn.title = enabled ? 'Benachrichtigungston aus' : 'Benachrichtigungston an';
        if (onIcon) onIcon.classList.toggle('hidden', !enabled);
        if (offIcon) offIcon.classList.toggle('hidden', enabled);
    }

    /**
     * Watches all overlays and disables sidebar interaction when any overlay is visible.
     * Uses a MutationObserver to detect class changes on overlay elements.
     */
    setupOverlayWatcher() {
        const checkOverlays = () => {
            const anyOverlayOpen = document.querySelectorAll(
                '.overlay:not(.hidden), .upload-modal:not(.hidden), .prompt-info-overlay'
            );
            // Filter: only count overlays that are actually visible (displayed)
            let isOpen = false;
            anyOverlayOpen.forEach(el => {
                if (el.offsetParent !== null || getComputedStyle(el).display !== 'none') {
                    isOpen = true;
                }
            });
            document.body.classList.toggle('overlay-active', isOpen);
        };

        // Observe class changes on all overlay elements
        const observer = new MutationObserver(checkOverlays);
        document.querySelectorAll('.overlay, .upload-modal').forEach(el => {
            observer.observe(el, { attributes: true, attributeFilter: ['class'] });
        });

        // Also observe the body for dynamically added overlays (prompt-info-overlay)
        const bodyObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === 1 && (node.classList?.contains('prompt-info-overlay') || node.classList?.contains('overlay'))) {
                        observer.observe(node, { attributes: true, attributeFilter: ['class'] });
                        checkOverlays();
                    }
                }
                for (const node of mutation.removedNodes) {
                    if (node.nodeType === 1 && node.classList?.contains('prompt-info-overlay')) {
                        checkOverlays();
                    }
                }
            }
        });
        bodyObserver.observe(document.body, { childList: true });

        // Initial check
        checkOverlays();
    }

    // ===== EDGE ACTIVATION ZONE (Desktop) =====
    _setupEdgeActivation() {
        const edgeZone = this.dom.sidebarEdgeZone;
        if (!edgeZone) return;

        let autoCloseTimer = null;

        const clearAutoClose = () => {
            if (autoCloseTimer) {
                clearTimeout(autoCloseTimer);
                autoCloseTimer = null;
            }
        };

        const startAutoClose = () => {
            clearAutoClose();
            autoCloseTimer = setTimeout(() => {
                if (!this.sessions.sidebarCollapsed) {
                    this.sessions.closeSidebar();
                }
            }, 3000);
        };

        // Track mouse position for glow effect
        document.addEventListener('mousemove', (e) => {
            if (document.body.classList.contains('overlay-active')) return;

            // When sidebar is open, track if mouse leaves sidebar area for auto-close
            if (!this.sessions.sidebarCollapsed) {
                const sidebarRect = this.dom.sidebar.getBoundingClientRect();
                if (e.clientX > sidebarRect.right + 20) {
                    if (!autoCloseTimer) startAutoClose();
                } else {
                    clearAutoClose();
                }
                return;
            }

            const viewportWidth = window.innerWidth;
            const mouseXPercent = (e.clientX / viewportWidth) * 100;

            // Glow intensifies within 20% zone
            if (mouseXPercent < 20) {
                const intensity = Math.max(0, 1 - (mouseXPercent / 20));
                const glowSpread = intensity * 30;
                edgeZone.style.setProperty('--glow-intensity', intensity.toFixed(2));
                edgeZone.style.setProperty('--glow-spread', glowSpread.toFixed(0));

                // Chevrons appear at 5%
                const chevrons = document.getElementById('edge-chevrons');
                if (chevrons) {
                    if (mouseXPercent <= 5) {
                        chevrons.classList.remove('hidden');
                    } else {
                        chevrons.classList.add('hidden');
                    }
                }
            } else {
                edgeZone.style.setProperty('--glow-intensity', '0');
                edgeZone.style.setProperty('--glow-spread', '0');
                const chevrons = document.getElementById('edge-chevrons');
                if (chevrons) chevrons.classList.add('hidden');
            }
        });

        // Click on chevrons opens sidebar
        const chevronEl = document.getElementById('edge-chevrons');
        if (chevronEl) {
            chevronEl.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.sessions.sidebarCollapsed && !document.body.classList.contains('overlay-active')) {
                    this.sessions.openSidebar();
                    edgeZone.style.setProperty('--glow-intensity', '0');
                    edgeZone.style.setProperty('--glow-spread', '0');
                    chevronEl.classList.add('hidden');
                }
            });
        }

        // Auto-close: track mouse entering/leaving sidebar
        this.dom.sidebar.addEventListener('mouseenter', () => {
            clearAutoClose();
        });

        this.dom.sidebar.addEventListener('mouseleave', () => {
            if (!this.sessions.sidebarCollapsed) {
                startAutoClose();
            }
        });
    }

    // ===== MOBILE SWIPE SUPPORT (Grab-Effekt) =====
    _setupMobileSwipe() {
        let touchStartX = 0;
        let touchStartY = 0;
        let isSwiping = false;
        let swipeDecided = false;
        let dragging = false;
        const EDGE_ZONE = 300;
        const sidebar = this.dom.sidebar;
        const sidebarWidth = 280; // matches --sidebar-width

        const setSidebarPosition = (offsetX) => {
            // Clamp between -sidebarWidth (fully hidden) and 0 (fully visible)
            const pos = Math.max(-sidebarWidth, Math.min(0, offsetX));
            sidebar.style.transition = 'none';
            sidebar.style.transform = `translateX(${pos}px)`;
        };

        const finishSwipe = (open) => {
            sidebar.style.transition = 'transform 0.25s ease';
            if (open) {
                sidebar.style.transform = 'translateX(0)';
                this.sessions.sidebarCollapsed = false;
                sidebar.classList.remove('collapsed');
            } else {
                sidebar.style.transform = `translateX(-${sidebarWidth}px)`;
                this.sessions.sidebarCollapsed = true;
                sidebar.classList.add('collapsed');
            }
            localStorage.setItem('sidebarCollapsed', this.sessions.sidebarCollapsed);
            // Reset inline styles after transition
            setTimeout(() => {
                sidebar.style.transition = '';
                sidebar.style.transform = '';
            }, 260);
        };

        document.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            isSwiping = false;
            swipeDecided = false;
            dragging = false;
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (document.body.classList.contains('overlay-active')) return;
            
            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            const deltaX = currentX - touchStartX;
            const absDeltaX = Math.abs(deltaX);
            const absDeltaY = Math.abs(currentY - touchStartY);

            // Decide swipe direction once
            if (!swipeDecided && (absDeltaX > 15 || absDeltaY > 15)) {
                if (absDeltaX > absDeltaY) {
                    isSwiping = true;
                    swipeDecided = true;

                    // Only allow opening from edge zone, closing from anywhere
                    if (this.sessions.sidebarCollapsed && touchStartX > EDGE_ZONE) {
                        isSwiping = false;
                    }
                } else {
                    swipeDecided = true;
                    isSwiping = false;
                }
            }

            if (!isSwiping) return;
            dragging = true;

            if (this.sessions.sidebarCollapsed) {
                // Opening: finger drags from left, sidebar follows
                const offset = -sidebarWidth + deltaX;
                setSidebarPosition(offset);
            } else {
                // Closing: finger drags left, sidebar follows
                if (deltaX < 0) {
                    setSidebarPosition(deltaX);
                }
            }
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!dragging) return;
            
            const endX = e.changedTouches[0].clientX;
            const deltaX = endX - touchStartX;

            if (this.sessions.sidebarCollapsed) {
                // Open if dragged more than 30% of sidebar width
                finishSwipe(deltaX > sidebarWidth * 0.3);
            } else {
                // Close if dragged left more than 30%
                finishSwipe(deltaX > -(sidebarWidth * 0.3));
            }

            isSwiping = false;
            swipeDecided = false;
            dragging = false;
        }, { passive: true });
    }
}

// Initialize the Chat App when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new ChatApp();
});
