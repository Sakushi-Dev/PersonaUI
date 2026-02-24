# Security Policy

## Supported Versions

PersonaUI is currently in **alpha**. Only the latest release receives security updates. Older alpha versions are not maintained.

| Version | Supported |
|---------|-----------|
| 0.3.x (latest) | Ô£à |
| 0.2.x | ÔØî |
| 0.1.x | ÔØî |

Once PersonaUI reaches a stable release (1.0.0), a long-term support model will be defined.

---

## Reporting a Vulnerability

If you discover a security vulnerability in PersonaUI, **please do not open a public GitHub Issue.**

Instead, report it privately via one of these channels:

- **GitHub Private Vulnerability Reporting** — Use the [Security tab](https://github.com/Sakushi-Dev/PersonaUI/security/advisories/new) of this repository to submit a private advisory.
- **Direct contact** — Alternatively, reach out to the maintainer directly via GitHub ([@Sakushi-Dev](https://github.com/Sakushi-Dev)).

### What to include

Please provide as much of the following as possible:

- A clear description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept or a minimal example)
- Affected version(s)
- Any suggested fix or patch, if available

### What to expect

| Timeline | Action |
|----------|--------|
| **Within 48 hours** | Acknowledgement of your report |
| **Within 7 days** | Initial assessment — confirmed, needs more info, or declined |
| **Within 30 days** | Patch release (for confirmed issues), or final decision |

If the vulnerability is **confirmed**, you will be credited in the release notes (unless you prefer to remain anonymous).

If the vulnerability is **declined** (e.g. out of scope or not reproducible), you will receive a clear explanation.

---

## Scope

The following are considered **in scope**:

- The Flask backend (`src/`) — routes, services, database access
- The React frontend (`frontend/src/`) — XSS, data exposure, insecure API calls
- Local file handling — path traversal, unintended file access
- API key exposure — any way the Anthropic API key could be leaked

The following are **out of scope**:

- Vulnerabilities in third-party dependencies (report those upstream)
- Issues requiring physical access to the machine running PersonaUI
- The Anthropic Claude API itself

---

## Disclosure Policy

We follow **coordinated disclosure**. Please allow us sufficient time to develop and release a fix before making the vulnerability public.
