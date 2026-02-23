// ── usePolling Hook ──

import { useEffect, useRef } from 'react';

export function usePolling(callback, interval = 5000, enabled = true) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || !interval) return;

    const tick = () => savedCallback.current();
    tick(); // Execute immediately
    const id = setInterval(tick, interval);

    return () => clearInterval(id);
  }, [interval, enabled]);
}
