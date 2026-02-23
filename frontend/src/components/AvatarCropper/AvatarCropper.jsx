// ── AvatarCropper Component ──

import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import Button from '../Button/Button';
import styles from './AvatarCropper.module.css';

export default function AvatarCropper({ file, onSave, onCancel }) {
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const [image, setImage] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(1);
  const [dragStart, setDragStart] = useState(null);

  const CANVAS_SIZE = 256;

  // Minimum scale: image must always cover the full canvas
  const minScale = useMemo(
    () => (image ? Math.max(CANVAS_SIZE / image.width, CANVAS_SIZE / image.height) : 0.1),
    [image]
  );

  // Clamp offset so the image edge never goes past the canvas boundary
  const clampOffset = useCallback((ox, oy, img, sc) => {
    if (!img) return { x: ox, y: oy };
    const imgW = img.width * sc;
    const imgH = img.height * sc;
    const maxX = Math.max(0, (imgW - CANVAS_SIZE) / 2);
    const maxY = Math.max(0, (imgH - CANVAS_SIZE) / 2);
    return {
      x: Math.max(-maxX, Math.min(maxX, ox)),
      y: Math.max(-maxY, Math.min(maxY, oy)),
    };
  }, []);

  // Load image from file prop if provided
  useEffect(() => {
    if (file) {
      const img = new Image();
      img.onload = () => {
        setImage(img);
        const fitScale = Math.max(CANVAS_SIZE / img.width, CANVAS_SIZE / img.height);
        setScale(fitScale);
        setOffset({ x: 0, y: 0 });
      };
      img.src = URL.createObjectURL(file);
      return () => URL.revokeObjectURL(img.src);
    }
  }, [file]);

  const drawImage = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    // Draw circular clip
    ctx.save();
    ctx.beginPath();
    ctx.arc(CANVAS_SIZE / 2, CANVAS_SIZE / 2, CANVAS_SIZE / 2, 0, Math.PI * 2);
    ctx.clip();

    const imgWidth = image.width * scale;
    const imgHeight = image.height * scale;
    const x = (CANVAS_SIZE - imgWidth) / 2 + offset.x;
    const y = (CANVAS_SIZE - imgHeight) / 2 + offset.y;

    ctx.drawImage(image, x, y, imgWidth, imgHeight);
    ctx.restore();

    // Draw circle border
    ctx.beginPath();
    ctx.arc(CANVAS_SIZE / 2, CANVAS_SIZE / 2, CANVAS_SIZE / 2 - 1, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 2;
    ctx.stroke();
  }, [image, offset, scale]);

  useEffect(() => {
    drawImage();
  }, [drawImage]);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const img = new Image();
    img.onload = () => {
      setImage(img);
      const fitScale = Math.max(CANVAS_SIZE / img.width, CANVAS_SIZE / img.height);
      setScale(fitScale);
      setOffset({ x: 0, y: 0 });
    };
    img.src = URL.createObjectURL(file);
  };

  const handleMouseDown = (e) => {
    setDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e) => {
    if (!dragging || !dragStart) return;
    const raw = { x: e.clientX - dragStart.x, y: e.clientY - dragStart.y };
    setOffset(clampOffset(raw.x, raw.y, image, scale));
  };

  const handleMouseUp = () => {
    setDragging(false);
    setDragStart(null);
  };

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    setScale((prev) => {
      const next = Math.max(minScale, Math.min(5, prev + delta));
      setOffset((off) => clampOffset(off.x, off.y, image, next));
      return next;
    });
  }, [image, minScale, clampOffset]);

  // ── Touch support (drag + pinch-to-zoom) ──
  const lastTouchRef = useRef(null);
  const lastPinchDistRef = useRef(null);

  const handleTouchStart = (e) => {
    if (e.touches.length === 1) {
      const t = e.touches[0];
      setDragging(true);
      setDragStart({ x: t.clientX - offset.x, y: t.clientY - offset.y });
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      lastPinchDistRef.current = Math.hypot(dx, dy);
    }
  };

  const handleTouchMove = useCallback((e) => {
    e.preventDefault();
    if (e.touches.length === 1 && dragging && dragStart) {
      const t = e.touches[0];
      const raw = { x: t.clientX - dragStart.x, y: t.clientY - dragStart.y };
      setOffset(clampOffset(raw.x, raw.y, image, scale));
    } else if (e.touches.length === 2 && lastPinchDistRef.current) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      const delta = (dist - lastPinchDistRef.current) * 0.005;
      setScale((prev) => {
        const next = Math.max(minScale, Math.min(5, prev + delta));
        setOffset((off) => clampOffset(off.x, off.y, image, next));
        return next;
      });
      lastPinchDistRef.current = dist;
    }
  }, [dragging, dragStart, image, scale, minScale, clampOffset]);

  const handleTouchEnd = () => {
    setDragging(false);
    setDragStart(null);
    lastPinchDistRef.current = null;
  };

  // Register touchmove + wheel as non-passive so preventDefault() works
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.addEventListener('touchmove', handleTouchMove, { passive: false });
    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      canvas.removeEventListener('touchmove', handleTouchMove);
      canvas.removeEventListener('wheel', handleWheel);
    };
  }, [handleTouchMove, handleWheel]);

  const handleSave = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob) onSave?.(blob);
    }, 'image/jpeg', 0.9);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.canvasContainer}>
        <canvas
          ref={canvasRef}
          width={CANVAS_SIZE}
          height={CANVAS_SIZE}
          className={styles.canvas}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        />
        {!image && (
          <div className={styles.placeholder} onClick={() => fileInputRef.current?.click()}>
            <span>📷</span>
            <span>Bild auswählen</span>
          </div>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className={styles.fileInput}
      />

      {image && (
        <div className={styles.controls}>
          <input
            type="range"
            min={minScale}
            max="5"
            step="0.05"
            value={scale}
            onChange={(e) => {
            const next = Math.max(minScale, parseFloat(e.target.value));
            setScale(next);
            setOffset((off) => clampOffset(off.x, off.y, image, next));
          }}
            className={styles.zoomSlider}
          />
          <span className={styles.zoomLabel}>Zoom</span>
        </div>
      )}

      <div className={styles.actions}>
        {!image && (
          <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
            Bild auswählen
          </Button>
        )}
        {image && (
          <>
            <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
              Anderes Bild
            </Button>
            <Button variant="primary" onClick={handleSave}>
              Speichern
            </Button>
          </>
        )}
        <Button variant="ghost" onClick={onCancel}>
          Abbrechen
        </Button>
      </div>
    </div>
  );
}
