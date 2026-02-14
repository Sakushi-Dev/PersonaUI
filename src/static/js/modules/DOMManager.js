/**
 * DOMManager - Manages all DOM element references
 */
export class DOMManager {
    constructor() {
        // Input elements
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.loadingAnimation = document.getElementById('loading-animation');
        
        // Sidebar elements
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebar-toggle');
        this.sidebarEdgeZone = document.getElementById('sidebar-edge-zone');
        this.edgeGlow = document.getElementById('edge-glow');
        this.sidebarBackBtn = document.getElementById('sidebar-back-btn');
        this.sidebarTitle = document.getElementById('sidebar-title');
        this.sidebarPersonaView = document.getElementById('sidebar-persona-view');
        this.sidebarSessionsView = document.getElementById('sidebar-sessions-view');
        this.sidebarPersonaList = document.getElementById('sidebar-persona-list');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.sessionsList = document.getElementById('sessions-list');
        this.chatHeader = document.querySelector('.chat-header');
        
        // Settings elements
        this.settingsDropdown = document.getElementById('settings-dropdown');
        this.settingsMenu = document.getElementById('settings-menu');
        this.editCharacterBtn = document.getElementById('edit-character-btn');
        this.characterOverlay = document.getElementById('character-settings-overlay');
        this.closeSettingsBtn = document.getElementById('close-settings');
        this.saveCharacterBtn = document.getElementById('save-character-btn');
        this.resetCharacterBtn = document.getElementById('reset-character-btn');
        
        // Persona list/creator view elements
        this.personaListView = document.getElementById('persona-list-view');
        this.personaCreatorView = document.getElementById('persona-creator-view');
        this.openPersonaCreatorBtn = document.getElementById('open-persona-creator-btn');
        this.backToPersonaListBtn = document.getElementById('back-to-persona-list');
        this.personaGrid = document.getElementById('persona-grid');
        this.creatorChangeAvatarBtn = document.getElementById('creator-change-avatar-btn');
        this.creatorAvatarPreview = document.getElementById('creator-avatar-preview');
        
        // Custom Specs elements
        this.openCustomSpecsBtn = document.getElementById('open-custom-specs-btn');
        this.customSpecsOverlay = document.getElementById('custom-specs-overlay');
        this.closeCustomSpecsBtn = document.getElementById('close-custom-specs');
        
        // API Key settings elements
        this.apiKeyBtn = document.getElementById('api-key-btn');
        this.apiKeyOverlay = document.getElementById('api-key-overlay');
        this.closeApiKeyBtn = document.getElementById('close-api-key');
        this.testApiKeyBtn = document.getElementById('test-api-key-btn');
        this.saveApiKeyBtn = document.getElementById('save-api-key-btn');
        this.apiKeyInput = document.getElementById('anthropic-api-key');
        this.apiKeyStatus = document.getElementById('api-key-status');
        this.pasteApiKeyBtn = document.getElementById('paste-api-key-btn');
        
        // Interface settings elements
        this.interfaceSettingsBtn = document.getElementById('interface-settings-btn');
        this.interfaceSettingsOverlay = document.getElementById('interface-settings-overlay');
        this.closeInterfaceSettingsBtn = document.getElementById('close-interface-settings');
        this.saveInterfaceBtn = document.getElementById('save-interface-btn');
        this.resetInterfaceBtn = document.getElementById('reset-interface-btn');
        
        // API settings elements
        this.apiSettingsBtn = document.getElementById('api-settings-btn');
        this.apiSettingsOverlay = document.getElementById('api-settings-overlay');
        this.closeApiSettingsBtn = document.getElementById('close-api-settings');
        this.saveApiSettingsBtn = document.getElementById('save-api-settings-btn');
        this.resetApiSettingsBtn = document.getElementById('reset-api-settings-btn');
        
        // Server settings elements
        this.serverSettingsBtn = document.getElementById('server-settings-btn');
        this.serverSettingsOverlay = document.getElementById('server-settings-overlay');
        this.closeServerSettingsBtn = document.getElementById('close-server-settings');
        this.closeServerSettingsCancelBtn = document.getElementById('close-server-settings-cancel');
        this.saveServerSettingsBtn = document.getElementById('save-server-settings-btn');
        
        // Avatar editor elements
        this.characterAvatarDisplay = document.getElementById('character-avatar-display');
        this.avatarEditorOverlay = document.getElementById('avatar-editor-overlay');
        this.closeAvatarEditorBtn = document.getElementById('close-avatar-editor');
        this.avatarGallery = document.getElementById('avatar-gallery');
        this.avatarSelectionStep = document.getElementById('avatar-selection-step');
        this.avatarBackBtn = document.getElementById('avatar-back-btn');
        this.avatarSaveBtn = document.getElementById('avatar-save-btn');
        
        // Upload elements
        this.avatarDropZone = document.getElementById('avatar-drop-zone');
        this.fileInput = document.getElementById('file-input');
        
        // User Profile elements
        this.userProfileBtn = document.getElementById('user-profile-btn');
        this.userProfileOverlay = document.getElementById('user-profile-overlay');
    }
}
