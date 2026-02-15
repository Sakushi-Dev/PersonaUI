// ── Date/Time Formatting ──

export function formatTimestamp(timestamp) {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  if (isNaN(date.getTime())) return timestamp;

  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const time = date.toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (isToday) return time;
  if (isYesterday) return `Gestern ${time}`;

  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(timestamp) {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Gerade eben';
  if (diffMins < 60) return `Vor ${diffMins} Min.`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `Vor ${diffHours} Std.`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'Gestern';
  if (diffDays < 7) return `Vor ${diffDays} Tagen`;

  return formatTimestamp(timestamp);
}

/**
 * Full date+time in German format: "DD.MM.YYYY · HH:MM"
 * Used for session items in the sidebar (matches legacy SessionManager.formatFullDateTime)
 */
export function formatFullDateTime(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(String(dateStr).replace(' ', 'T'));
    if (isNaN(date.getTime())) return dateStr;

    const dateFormatted = date.toLocaleDateString('de-DE', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
    const timeFormatted = date.toLocaleTimeString('de-DE', {
      hour: '2-digit', minute: '2-digit',
    });

    return `${dateFormatted} · ${timeFormatted}`;
  } catch {
    return dateStr;
  }
}

/**
 * Smart short date for persona contact time.
 * Today → "HH:MM", Yesterday → "Gestern", else "DD.MM.YY"
 * Matches legacy SessionManager.formatDateTime
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(String(dateStr).replace(' ', 'T'));
    if (isNaN(date.getTime())) return dateStr;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    const timeStr = date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });

    if (dateOnly.getTime() === today.getTime()) return timeStr;
    if (dateOnly.getTime() === yesterday.getTime()) return 'Gestern';

    return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
  } catch {
    return dateStr;
  }
}
