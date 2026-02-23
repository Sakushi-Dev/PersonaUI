// ── Toast Notification System ──

import { createContext, useContext, useState, useCallback, useRef } from 'react';
import Toast from './Toast';
import styles from './Toast.module.css';

const ToastContext = createContext(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastContainer');
  return context;
}

export default function ToastContainer({ children }) {
  const [toasts, setToasts] = useState([]);
  const idCounter = useRef(0);

  const showNotification = useCallback((message, type = 'info', duration = 3000) => {
    const id = ++idCounter.current;
    setToasts((prev) => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showNotification, removeToast }}>
      {children}
      <div className={styles.container}>
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
