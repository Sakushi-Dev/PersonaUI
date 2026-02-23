// ── useSwipe Hook ──

import { useRef, useCallback } from 'react';

export function useSwipe({ onSwipeRight, onSwipeLeft, edgeZone = 30, threshold = 0.3 }) {
  const touchStart = useRef(null);
  const touchDelta = useRef(0);

  const handleTouchStart = useCallback((e) => {
    const touch = e.touches[0];
    // Only track if starting from left edge (for opening)
    if (touch.clientX < edgeZone || onSwipeLeft) {
      touchStart.current = { x: touch.clientX, y: touch.clientY };
      touchDelta.current = 0;
    }
  }, [edgeZone, onSwipeLeft]);

  const handleTouchMove = useCallback((e) => {
    if (!touchStart.current) return;
    const touch = e.touches[0];
    touchDelta.current = touch.clientX - touchStart.current.x;
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (!touchStart.current) return;

    const swipeDistance = touchDelta.current;
    const screenWidth = window.innerWidth;
    const swipePercent = Math.abs(swipeDistance) / screenWidth;

    if (swipePercent >= threshold) {
      if (swipeDistance > 0) {
        onSwipeRight?.();
      } else {
        onSwipeLeft?.();
      }
    }

    touchStart.current = null;
    touchDelta.current = 0;
  }, [threshold, onSwipeRight, onSwipeLeft]);

  return {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
  };
}
