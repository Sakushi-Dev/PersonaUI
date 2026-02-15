// ── Message Formatting Utilities ──

/**
 * Format non-verbal text: *text* → <span class="non_verbal">text</span>
 * Skips content inside code blocks (``` fenced blocks)
 */
export function formatNonVerbal(text) {
  if (!text) return '';
  return text.replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
}

/**
 * Escape HTML special characters for safe rendering inside code blocks
 */
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Convert markdown fenced code blocks (```...```) to styled HTML
 */
export function formatCodeBlocks(text) {
  if (!text) return text;
  return text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, _lang, code) => {
    const escaped = escapeHtml(code.replace(/^\n+|\n+$/g, ''));
    return `<div class="code-block"><pre><code>${escaped}</code></pre></div>`;
  });
}

/**
 * Convert newlines to <br> tags, but skip content inside code blocks
 */
export function formatLineBreaks(text) {
  if (!text) return '';

  // Split by code blocks to avoid converting newlines inside them
  const parts = text.split(/(<div class="code-block">[\s\S]*?<\/div>)/g);
  return parts
    .map((part, i) => {
      // Odd indices are code blocks — leave them alone
      if (i % 2 === 1) return part;
      // Remove leading newlines and convert rest
      return part.replace(/^\n+/, '').replace(/\n/g, '<br>');
    })
    .join('');
}

/**
 * Full message formatting pipeline
 */
export function formatMessage(text) {
  if (!text) return '';
  let formatted = text.trim();
  // Strip leading --- separators (used by streaming)
  formatted = formatted.replace(/^\s*---\s*/, '');
  // Code blocks first (before line breaks and non-verbal)
  formatted = formatCodeBlocks(formatted);
  formatted = formatLineBreaks(formatted);
  formatted = formatNonVerbal(formatted);
  return formatted;
}
