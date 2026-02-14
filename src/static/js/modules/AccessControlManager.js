/**
 * AccessControlManager – IP-basierte Zugangskontrolle
 * 
 * Pollt ausstehende Zugangsanfragen und zeigt Notifications/Overlay an.
 * Nur aktiv auf dem lokalen Gerät (Host).
 */
export class AccessControlManager {
    constructor(dom) {
        this.dom = dom;
        this.pollInterval = null;
        this.knownPending = new Set();
        this.isLocal = true; // Wird beim Init geprüft
        
        // DOM-Elemente
        this.overlay = document.getElementById('access-control-overlay');
        this.closeBtn = document.getElementById('close-access-control');
        this.closeCancelBtn = document.getElementById('close-access-control-cancel');
        this.pendingList = document.getElementById('pending-requests-list');
        this.whitelistEntries = document.getElementById('whitelist-entries');
        this.blacklistEntries = document.getElementById('blacklist-entries');
        this.whitelistCount = document.getElementById('whitelist-count');
        this.blacklistCount = document.getElementById('blacklist-count');
        this.notification = document.getElementById('access-notification');
        this.notificationIp = document.getElementById('access-notification-ip');
        this.notificationApproveBtn = document.getElementById('notification-approve-btn');
        this.notificationDenyBtn = document.getElementById('notification-deny-btn');
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Overlay schließen
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.closeOverlay());
        }
        if (this.closeCancelBtn) {
            this.closeCancelBtn.addEventListener('click', () => this.closeOverlay());
        }
        
        // Notification-Buttons (Quick-Actions)
        if (this.notificationApproveBtn) {
            this.notificationApproveBtn.addEventListener('click', () => {
                const ip = this.notificationIp?.textContent;
                if (ip) this.approveIp(ip);
            });
        }
        if (this.notificationDenyBtn) {
            this.notificationDenyBtn.addEventListener('click', () => {
                const ip = this.notificationIp?.textContent;
                if (ip) this.denyIp(ip);
            });
        }
    }
    
    /**
     * Startet das Polling für ausstehende Anfragen.
     * Wird nur aufgerufen, wenn der Server im Listen-Modus ist.
     */
    startPolling() {
        if (this.pollInterval) return;
        
        // Sofort einmal prüfen
        this.checkPendingRequests();
        
        // Alle 3 Sekunden prüfen
        this.pollInterval = setInterval(() => {
            this.checkPendingRequests();
        }, 3000);
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    async checkPendingRequests() {
        try {
            const response = await fetch('/api/access/pending');
            const data = await response.json();
            
            if (!data.success) return;
            
            const pending = data.pending || {};
            const pendingIps = Object.keys(pending);
            
            // Neue Anfragen erkennen und Notification zeigen
            for (const ip of pendingIps) {
                if (!this.knownPending.has(ip)) {
                    this.knownPending.add(ip);
                    this.showNotification(ip);
                }
            }
            
            // Entfernte Anfragen aufräumen
            for (const ip of this.knownPending) {
                if (!pendingIps.includes(ip)) {
                    this.knownPending.delete(ip);
                }
            }
            
            // Wenn Overlay offen ist, Liste aktualisieren
            if (this.overlay && !this.overlay.classList.contains('hidden')) {
                this.renderPendingList(pending);
            }
            
            // Notification verstecken wenn keine Anfragen mehr
            if (pendingIps.length === 0 && this.notification) {
                this.notification.classList.add('hidden');
            }
            
        } catch (error) {
            // Stille Fehler – Polling soll nicht abstürzen
        }
    }
    
    showNotification(ip) {
        if (!this.notification || !this.notificationIp) return;
        
        this.notificationIp.textContent = ip;
        this.notification.classList.remove('hidden');
        
        // Dezente Animation
        this.notification.classList.remove('access-notification-enter');
        void this.notification.offsetWidth; // Force reflow
        this.notification.classList.add('access-notification-enter');
    }
    
    hideNotification() {
        if (this.notification) {
            this.notification.classList.add('hidden');
        }
    }
    
    // ===== Overlay: Öffnen/Schließen =====
    
    async openOverlay() {
        if (!this.overlay) return;
        
        this.overlay.classList.remove('hidden');
        await this.loadAllData();
    }
    
    closeOverlay() {
        if (this.overlay) {
            this.overlay.classList.add('hidden');
        }
    }
    
    async loadAllData() {
        await Promise.all([
            this.loadPendingRequests(),
            this.loadAccessLists()
        ]);
    }
    
    // ===== Daten laden =====
    
    async loadPendingRequests() {
        try {
            const response = await fetch('/api/access/pending');
            const data = await response.json();
            
            if (data.success) {
                this.renderPendingList(data.pending || {});
            }
        } catch (error) {
            console.error('Fehler beim Laden der Pending-Requests:', error);
        }
    }
    
    async loadAccessLists() {
        try {
            const response = await fetch('/api/access/lists');
            const data = await response.json();
            
            if (data.success) {
                this.renderWhitelist(data.whitelist || []);
                this.renderBlacklist(data.blacklist || []);
            }
        } catch (error) {
            console.error('Fehler beim Laden der Access-Listen:', error);
        }
    }
    
    // ===== Rendering =====
    
    renderPendingList(pending) {
        if (!this.pendingList) return;
        
        const entries = Object.entries(pending);
        
        if (entries.length === 0) {
            this.pendingList.innerHTML = '<div class="access-empty-state">Keine ausstehenden Anfragen</div>';
            return;
        }
        
        this.pendingList.innerHTML = entries.map(([ip, data]) => `
            <div class="access-entry access-entry-pending" data-ip="${ip}">
                <div class="access-entry-info">
                    <span class="access-ip">${ip}</span>
                    <span class="access-meta">Wartet seit ${this.formatWaitTime(data.waiting_seconds)}</span>
                </div>
                <div class="access-entry-actions">
                    <button class="access-btn access-btn-approve" onclick="window._accessControl.approveIp('${ip}')" title="Genehmigen">✓</button>
                    <button class="access-btn access-btn-deny" onclick="window._accessControl.denyIp('${ip}')" title="Ablehnen">✕</button>
                </div>
            </div>
        `).join('');
    }
    
    renderWhitelist(whitelist) {
        if (!this.whitelistEntries) return;
        if (this.whitelistCount) this.whitelistCount.textContent = whitelist.length;
        
        if (whitelist.length === 0) {
            this.whitelistEntries.innerHTML = '<div class="access-empty-state">Keine Einträge</div>';
            return;
        }
        
        this.whitelistEntries.innerHTML = whitelist.map(ip => `
            <div class="access-entry access-entry-whitelisted" data-ip="${ip}">
                <div class="access-entry-info">
                    <span class="access-ip">${ip}</span>
                </div>
                <div class="access-entry-actions">
                    <button class="access-btn access-btn-remove" onclick="window._accessControl.removeFromWhitelist('${ip}')" title="Entfernen">✕</button>
                </div>
            </div>
        `).join('');
    }
    
    renderBlacklist(blacklist) {
        if (!this.blacklistEntries) return;
        if (this.blacklistCount) this.blacklistCount.textContent = blacklist.length;
        
        if (blacklist.length === 0) {
            this.blacklistEntries.innerHTML = '<div class="access-empty-state">Keine Einträge</div>';
            return;
        }
        
        this.blacklistEntries.innerHTML = blacklist.map(ip => `
            <div class="access-entry access-entry-blacklisted" data-ip="${ip}">
                <div class="access-entry-info">
                    <span class="access-ip">${ip}</span>
                </div>
                <div class="access-entry-actions">
                    <button class="access-btn access-btn-unblock" onclick="window._accessControl.removeFromBlacklist('${ip}')" title="Entsperren">↩</button>
                </div>
            </div>
        `).join('');
    }
    
    formatWaitTime(seconds) {
        if (seconds < 60) return `${seconds}s`;
        const min = Math.floor(seconds / 60);
        const sec = seconds % 60;
        return `${min}m ${sec}s`;
    }
    
    // ===== Aktionen =====
    
    async approveIp(ip) {
        try {
            const response = await fetch('/api/access/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await response.json();
            
            if (data.success) {
                this.knownPending.delete(ip);
                this.hideNotification();
                await this.loadAllData();
            }
        } catch (error) {
            console.error('Fehler beim Genehmigen:', error);
        }
    }
    
    async denyIp(ip) {
        try {
            const response = await fetch('/api/access/deny', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await response.json();
            
            if (data.success) {
                this.knownPending.delete(ip);
                this.hideNotification();
                await this.loadAllData();
            }
        } catch (error) {
            console.error('Fehler beim Ablehnen:', error);
        }
    }
    
    async removeFromWhitelist(ip) {
        try {
            const response = await fetch('/api/access/whitelist/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await response.json();
            
            if (data.success) {
                await this.loadAccessLists();
            }
        } catch (error) {
            console.error('Fehler beim Entfernen aus Whitelist:', error);
        }
    }
    
    async removeFromBlacklist(ip) {
        try {
            const response = await fetch('/api/access/blacklist/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await response.json();
            
            if (data.success) {
                await this.loadAccessLists();
            }
        } catch (error) {
            console.error('Fehler beim Entfernen aus Blacklist:', error);
        }
    }
}
