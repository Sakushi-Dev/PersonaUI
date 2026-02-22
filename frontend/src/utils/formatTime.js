// ── Date/Time Formatting ──

import { t as translate } from './i18n';

function locale(lang) {
  return lang === 'de' ? 'de-DE' : 'en-US';
}

export function formatTimestamp(timestamp, language = 'de') {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  if (isNaN(date.getTime())) return timestamp;

  const s = translate(language, 'formatTime');
  const loc = locale(language);

  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const time = date.toLocaleTimeString(loc, {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (isToday) return time;
  if (isYesterday) return `${s.yesterday} ${time}`;

  return date.toLocaleDateString(loc, {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(timestamp, language = 'de') {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const s = translate(language, 'formatTime');

  if (diffMins < 1) return s.justNow;
  if (diffMins < 60) return s.minutesAgo.replace('{n}', diffMins);

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return s.hoursAgo.replace('{n}', diffHours);

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return s.yesterday;
  if (diffDays < 7) return s.daysAgo.replace('{n}', diffDays);

  return formatTimestamp(timestamp, language);
}

/**
 * Full date+time: "DD.MM.YYYY · HH:MM"
 * Used for session items in the sidebar
 */
export function formatFullDateTime(dateStr, language = 'de') {
  if (!dateStr) return '';
  try {
    const date = new Date(String(dateStr).replace(' ', 'T'));
    if (isNaN(date.getTime())) return dateStr;

    const loc = locale(language);
    const dateFormatted = date.toLocaleDateString(loc, {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
    const timeFormatted = date.toLocaleTimeString(loc, {
      hour: '2-digit', minute: '2-digit',
    });

    return `${dateFormatted} · ${timeFormatted}`;
  } catch {
    return dateStr;
  }
}

/**
 * Smart short date for persona contact time.
 * Today → "HH:MM", Yesterday → translated, else "DD.MM.YY"
 */
export function formatDateTime(dateStr, language = 'de') {
  if (!dateStr) return '';
  try {
    const date = new Date(String(dateStr).replace(' ', 'T'));
    if (isNaN(date.getTime())) return dateStr;

    const s = translate(language, 'formatTime');
    const loc = locale(language);

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    const timeStr = date.toLocaleTimeString(loc, { hour: '2-digit', minute: '2-digit' });

    if (dateOnly.getTime() === today.getTime()) return timeStr;
    if (dateOnly.getTime() === yesterday.getTime()) return s.yesterday;

    return date.toLocaleDateString(loc, { day: '2-digit', month: '2-digit', year: '2-digit' });
  } catch {
    return dateStr;
  }
}
