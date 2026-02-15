// ── QRCodeOverlay ──
// Show QR code for network access or prompt to enable public mode

import { useState, useEffect } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import OverlayBody from '../../components/Overlay/OverlayBody';
import OverlayFooter from '../../components/Overlay/OverlayFooter';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { getServerSettings, getQRCode, getNetworkInfo } from '../../services/serverApi';
import styles from './Overlays.module.css';

export default function QRCodeOverlay({ open, onClose, onOpenServerSettings }) {
  const [serverMode, setServerMode] = useState(null);
  const [qrImage, setQrImage] = useState(null);
  const [ips, setIps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open) return;
    setLoading(true);

    Promise.all([
      getServerSettings(),
      getNetworkInfo().catch(() => ({ ips: [] })),
    ]).then(([settings, network]) => {
      setServerMode(settings.server_mode || 'local');
      setIps(network.ips || []);

      if (settings.server_mode === 'public') {
        return getQRCode().then((data) => {
          setQrImage(data.qr_code || data.image || null);
        }).catch(() => {});
      }
    }).finally(() => setLoading(false));
  }, [open]);

  const isPublic = serverMode === 'public';

  return (
    <Overlay open={open} onClose={onClose} width="420px">
      <OverlayHeader title="📱 Netzwerk-Zugriff" onClose={onClose} />
      <OverlayBody>
        {loading ? (
          <Spinner />
        ) : isPublic ? (
          <div className={styles.qrContent}>
            {qrImage && (
              <div className={styles.qrCode}>
                <img src={`data:image/png;base64,${qrImage}`} alt="QR Code" />
              </div>
            )}
            <div className={styles.ipList}>
              <p className={styles.settingLabel}>Netzwerk-Adressen:</p>
              {ips.map((ip, i) => (
                <code key={i} className={styles.ipAddress}>{ip}</code>
              ))}
            </div>
            <p className={styles.hint}>
              Dein Handy muss mit dem selben WLAN-Netzwerk verbunden sein.
            </p>
          </div>
        ) : (
          <div className={styles.centeredContent}>
            <span className={styles.bigIcon}>🔒</span>
            <p>Kein öffentlicher Zugang</p>
            <p className={styles.hint}>
              Der Server läuft im lokalen Modus. Ändere den Server-Modus, um Netzwerkzugriff zu ermöglichen.
            </p>
          </div>
        )}
      </OverlayBody>
      <OverlayFooter>
        {!isPublic && !loading && (
          <Button variant="primary" onClick={() => { onClose(); onOpenServerSettings?.(); }}>
            Server-Einstellungen öffnen
          </Button>
        )}
        <Button variant="secondary" onClick={onClose}>Schließen</Button>
      </OverlayFooter>
    </Overlay>
  );
}
