// ── Built-in Slash Commands ──
// Import this file once at app startup to register all default commands.

import { register } from './slashCommandRegistry';
import { t as translate } from '../../../utils/i18n';

// /reload – Reloads the browser page
register({
  name: 'reload',
  description: 'Seite neu laden',
  execute() {
    window.location.reload();
  },
});

// /rebuild – Starts the build_frontend.bat in a separate console window on the server
register({
  name: 'rebuild',
  description: 'React-Frontend neu kompilieren (eigenes Fenster)',
  async execute({ language } = {}) {
    const s = translate(language || 'en', 'slashCommands');
    console.log('[SlashCommand] /rebuild – starte Build-Script …');

    try {
      const res = await fetch('/api/commands/rebuild-frontend', { method: 'POST' });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        const msg = data.error || s.unknownError;
        console.error('[SlashCommand] /rebuild fehlgeschlagen:', msg);
        alert(`${s.buildFailed}\n${msg}`);
        return;
      }

      console.log('[SlashCommand] /rebuild – Build-Fenster geöffnet.');
    } catch (err) {
      console.error('[SlashCommand] /rebuild Netzwerk-Fehler:', err);
    }
  },
});

// ────────────────────────────────────────
// Add new commands below. Example:
//
// register({
//   name: 'clear',
//   description: 'Chat-Verlauf leeren',
//   execute({ args }) {
//     // custom logic here
//   },
// });
// ────────────────────────────────────────

// /onboarding – Start-Sequenz (Onboarding) erneut aktivieren
register({
  name: 'onboarding',
  description: 'Start-Sequenz (Onboarding) erneut aktivieren',
  async execute({ language } = {}) {
    const s = translate(language || 'en', 'slashCommands');
    console.log('[SlashCommand] /onboarding – setze Onboarding zurück …');

    try {
      const res = await fetch('/api/commands/reset-onboarding', { method: 'POST' });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        const msg = data.error || s.unknownError;
        console.error('[SlashCommand] /onboarding fehlgeschlagen:', msg);
        alert(`${s.onboardingFailed}\n${msg}`);
        return;
      }

      console.log('[SlashCommand] /onboarding – Onboarding zurückgesetzt, lade Seite neu …');
      window.location.reload();
    } catch (err) {
      console.error('[SlashCommand] /onboarding Netzwerk-Fehler:', err);
    }
  },
});

// /cortex – Sofort Cortex-Update auslösen und Zähler auf 0 zurücksetzen
register({
  name: 'cortex',
  description: 'Cortex-Update sofort auslösen (Zähler wird zurückgesetzt)',
  async execute({ sessionId, language } = {}) {
    const s = translate(language || 'en', 'slashCommands');
    console.log('[SlashCommand] /cortex – starte manuellen Cortex-Update …', { sessionId });

    try {
      const res = await fetch('/api/commands/cortex-update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId || null }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        const msg = data.error || s.unknownError;
        console.error('[SlashCommand] /cortex fehlgeschlagen:', msg);
        window.dispatchEvent(
          new CustomEvent('cortex-command-error', {
            detail: { error: msg },
          })
        );
        return;
      }

      console.log('[SlashCommand] /cortex – Update gestartet.');

      // Dispatch cortex-progress event so the CortexUpdateIndicator shows
      if (data.cortex) {
        window.dispatchEvent(
          new CustomEvent('cortex-progress', {
            detail: {
              triggered: true,
              progress: data.cortex.progress || { progress_percent: 0 },
              frequency: data.cortex.frequency,
              manual: true,
            },
          })
        );
      }
    } catch (err) {
      console.error('[SlashCommand] /cortex Netzwerk-Fehler:', err);
      window.dispatchEvent(
        new CustomEvent('cortex-command-error', {
          detail: { error: err.message },
        })
      );
    }
  },
});

// /mood – Open mood statistics and settings overlay
register({
  name: 'mood',
  description: 'Mood-Stats und Einstellungen öffnen',
  execute() {
    window.dispatchEvent(new CustomEvent('open-mood-overlay'));
  },
});
