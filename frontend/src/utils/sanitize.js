// ── HTML Sanitizing ──

const ALLOWED_TAGS = new Set([
  'b', 'i', 'em', 'strong', 'br', 'span', 'p', 'div',
  'code', 'pre', 'ul', 'ol', 'li', 'a', 'img',
]);

const ALLOWED_ATTRS = new Set(['class', 'href', 'src', 'alt', 'target', 'rel']);

/**
 * Basic HTML sanitizer — strips dangerous tags/attributes
 * For a production app, consider using DOMPurify
 */
export function sanitizeHtml(html) {
  if (!html) return '';
  // Remove script tags and event handlers
  let clean = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  clean = clean.replace(/\son\w+="[^"]*"/gi, '');
  clean = clean.replace(/\son\w+='[^']*'/gi, '');
  clean = clean.replace(/javascript:/gi, '');
  return clean;
}
