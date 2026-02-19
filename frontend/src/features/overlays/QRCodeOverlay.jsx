// ── QRCodeOverlay ──
// Show QR code for network access or prompt to enable public mode

import { useState, useEffect } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getServerSettings, getLocalIps, generateQRCode } from '../../services/serverApi';
import styles from './Overlays.module.css';

export default function QRCodeOverlay({ open, onClose, onOpenServerSettings }) {
  const [serverMode, setServerMode] = useState(null);
  const [qrImage, setQrImage] = useState(null);
  const [ipEntries, setIpEntries] = useState([]);  // { ip, port, url, type }
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setQrImage(null);
    setIpEntries([]);

    getServerSettings()
      .then(async (settings) => {
        const mode = settings.server_mode || 'local';
        setServerMode(mode);

        if (mode === 'listen') {
          // Fetch IPs + port, then generate QR code (like legacy)
          const ipData = await getLocalIps().catch(() => ({ ip_addresses: [], port: 5000 }));
          const addresses = ipData.ip_addresses || [];
          const port = ipData.port || 5000;

          const entries = addresses.map((ip) => ({
            ip,
            port,
            url: `http://${ip}:${port}`,
            type: ip.includes(':') ? 'IPv6' : 'IPv4',
          }));
          setIpEntries(entries);

          if (entries.length > 0) {
            const qrData = await generateQRCode(entries[0].url).catch(() => null);
            if (qrData?.qr_code) {
              setQrImage(qrData.qr_code);
            }
          }
        }
      })
      .catch(() => setServerMode('local'))
      .finally(() => setLoading(false));
  }, [open]);

  const isListen = serverMode === 'listen';

  return (
    <Overlay open={open} onClose={onClose} width="420px">
      <OverlayHeader title="📱 Netzwerk-Zugriff" onClose={onClose} />
      <OverlayBody>
        {loading ? (
          <Spinner />
        ) : isListen ? (
          <div className={styles.qrContent}>
            {qrImage && (
              <div className={styles.qrCode}>
                <img src={qrImage} alt="QR Code" />
              </div>
            )}
            <div className={styles.ipList}>
              <p className={styles.settingLabel}>📡 Netzwerk-Adressen:</p>
              {ipEntries.map((entry, i) => (
                <div key={i} className={styles.ipEntry}>
                  <span className={styles.ipType}>{entry.type}:</span>
                  <a
                    href={entry.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.ipLink}
                  >
                    {entry.url}
                  </a>
                </div>
              ))}
            </div>
            <div className={styles.tipBox}>
              <p className={styles.hint}>
                💡 <strong>Hinweis:</strong> Dein Handy muss mit dem selben WLAN-Netzwerk verbunden sein.
              </p>
            </div>
          </div>
        ) : (
          <div className={styles.centeredContent}>
            <span className={styles.bigIcon}>🔒</span>
            <h3>Kein öffentlicher Zugang</h3>
            <p className={styles.hint}>
              Der Server läuft aktuell im <strong>lokalen Modus</strong>.
              Um von anderen Geräten im Netzwerk darauf zuzugreifen, aktiviere den öffentlichen Modus in den Server-Einstellungen.
            </p>
          </div>
        )}
      </OverlayBody>
      <OverlayFooter>
        {!isListen && !loading && (
          <Button variant="primary" onClick={() => { onClose(); onOpenServerSettings?.(); }}>
            ⚙️ Server-Einstellungen öffnen
          </Button>
        )}
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
      </OverlayFooter>
    </Overlay>
  );
}
