/**
 * QRCodeManager - Verwaltet QR-Code Anzeige und Netzwerk-Zugriff
 */
export class QRCodeManager {
    constructor() {
        this.overlay = document.getElementById('qr-code-overlay');
        this.qrBtn = document.getElementById('qr-code-btn');
        this.closeBtn = document.getElementById('close-qr-code-overlay');
        this.availableSection = document.getElementById('qr-code-available');
        this.unavailableSection = document.getElementById('qr-code-unavailable');
        this.qrCanvas = document.getElementById('qr-code-canvas');
        this.ipList = document.getElementById('qr-code-ip-list');
        this.openServerSettingsBtn = document.getElementById('open-server-settings-from-qr');
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // QR Code Button im Header
        this.qrBtn.addEventListener('click', () => this.open());
        
        // Close Button
        this.closeBtn.addEventListener('click', () => this.close());
        
        // Overlay schließen beim Klick außerhalb
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });
        
        // Server Settings öffnen
        this.openServerSettingsBtn.addEventListener('click', () => {
            this.close();
            // Trigger Server Settings Overlay
            document.getElementById('server-settings-btn').click();
        });
    }
    
    async open() {
        try {
            // Prüfe Server-Modus
            const response = await fetch('/api/get_server_settings');
            const data = await response.json();
            
            if (data.success && data.server_mode === 'listen') {
                // Öffentlicher Zugang verfügbar
                await this.showQRCode();
            } else {
                // Kein öffentlicher Zugang
                this.showUnavailable();
            }
            
            this.overlay.classList.remove('hidden');
        } catch (error) {
            console.error('Fehler beim Laden der QR-Code Informationen:', error);
            this.showUnavailable();
            this.overlay.classList.remove('hidden');
        }
    }
    
    async showQRCode() {
        try {
            // Hole IP-Adressen
            const response = await fetch('/api/get_local_ips');
            const data = await response.json();
            
            if (data.success && data.ip_addresses && data.ip_addresses.length > 0) {
                // Zeige QR Code Section
                this.availableSection.classList.remove('hidden');
                this.unavailableSection.classList.add('hidden');
                
                // Generiere QR Code für erste IP-Adresse
                const primaryIP = data.ip_addresses[0];
                const port = data.port || 5000;
                const url = `http://${primaryIP}:${port}`;
                
                await this.generateQRCode(url);
                
                // Zeige IP-Adressen
                this.displayIPAddresses(data.ip_addresses, port);
            } else {
                this.showUnavailable();
            }
        } catch (error) {
            console.error('Fehler beim Generieren des QR-Codes:', error);
            this.showUnavailable();
        }
    }
    
    async generateQRCode(url) {
        try {
            const response = await fetch('/api/generate_qr_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            
            const data = await response.json();
            
            if (data.success && data.qr_code) {
                // Lade QR Code in Canvas
                const img = new Image();
                img.onload = () => {
                    const ctx = this.qrCanvas.getContext('2d');
                    this.qrCanvas.width = img.width;
                    this.qrCanvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                };
                // QR-Code ist bereits als data URL formatiert
                img.src = data.qr_code;
            }
        } catch (error) {
            console.error('Fehler beim Generieren des QR-Codes:', error);
        }
    }
    
    displayIPAddresses(ipAddresses, port) {
        let html = '';
        ipAddresses.forEach(ip => {
            const url = `http://${ip}:${port}`;
            const type = ip.includes(':') ? 'IPv6' : 'IPv4';
            html += `
                <div class="qr-ip-item">
                    <span class="qr-ip-type">${type}:</span>
                    <a href="${url}" target="_blank" class="qr-ip-link">${url}</a>
                </div>
            `;
        });
        this.ipList.innerHTML = html;
    }
    
    showUnavailable() {
        this.availableSection.classList.add('hidden');
        this.unavailableSection.classList.remove('hidden');
    }
    
    close() {
        this.overlay.classList.add('hidden');
    }
}
