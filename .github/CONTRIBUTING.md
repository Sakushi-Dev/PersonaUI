# Contributing to PersonaUI

Thank you for your interest in contributing to **PersonaUI**! This document explains how to set up your development environment, the workflow for submitting changes, and the standards we follow.

---

## Table of Contents

1. [Ways to Contribute](#ways-to-contribute)
2. [Development Setup](#development-setup)
3. [Branching & PR Workflow](#branching--pr-workflow)
4. [Code Style](#code-style)
5. [Testing](#testing)
6. [Commit Messages](#commit-messages)
7. [License](#license)

---

## Ways to Contribute

- **Bug reports** — Open a [GitHub Issue](https://github.com/Sakushi-Dev/PersonaUI/issues) and label it `bug`. Include steps to reproduce, expected behavior, and actual behavior.
- **Feature requests** — Open an issue labeled `enhancement`. Describe the use case and why it fits the project.
- **Pull Requests** — For fixes or new features. Always target the `dev` branch, never `main`. See the workflow below.
- **Documentation** — Improvements to `README.md`, `.github/docs/`, or inline code comments are always welcome.
- **Translations** — Locale files live in `frontend/src/locales/`. Currently English (`en`) and German (`de`) are supported.

---

## Development Setup

### Prerequisites

| Tool    | Min. Version | Notes                                    |
|---------|--------------|------------------------------------------|
| Python  | 3.12         | Use `pyenv` or `py` launcher on Windows  |
| Node.js | 22           | Required for the React frontend          |
| Git     | any          | -                                        |

### 1 — Clone & branch

```bash
git clone https://github.com/Sakushi-Dev/PersonaUI.git
cd PersonaUI
git checkout dev
git checkout -b feat/your-feature-name
```

### 2 — Python backend

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3 — React frontend

```bash
cd frontend
npm install
npm run dev   # starts Vite dev server on :5173
```

### 4 — Run the full application

```bash
# From the project root (with .venv active)
python src/app.py --no-gui   # browser-only mode (dev-friendly)
# or
python src/app.py            # opens native PyWebView window
```

The Flask backend runs on `http://localhost:5000`. In `--no-gui` mode, open `http://localhost:5000` in your browser.

---

## Branching & PR Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Stable release branch — **never commit directly** |
| `dev` | Integration branch — all PRs target here |
| `feat/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation-only changes |
| `refactor/*` | Code restructuring without behavior change |

**Steps:**

1. Fork the repository (external contributors) or create a branch from `dev` (collaborators).
2. Make your changes in small, focused commits.
3. Ensure all tests pass (`pytest`) and the frontend lints cleanly (`npm run lint`).
4. Open a Pull Request against `dev`. Fill in the PR template.
5. A maintainer will review and merge (or request changes).

---

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Maximum line length: **100 characters**.
- Use type hints where practical.
- Docstrings for all public functions and classes (Google style preferred).
- No unused imports — clean them up before committing.

### JavaScript / JSX (React)

- Follow the existing ESLint config (`frontend/eslint.config.js`).
- Run `npm run lint` before opening a PR and fix all reported issues.
- Use CSS Modules for component styling — no inline style objects.
- Prefer functional components with hooks; avoid class components.

---

## Testing

Tests live in the `src/tests/` directory and are run with **pytest**.

```bash
# Run all tests
pytest

# Run a specific file
pytest src/tests/test_api_client.py

# Run with output
pytest -s
```

- Add tests for any new backend logic you introduce.
- Test files follow the pattern `test_*.py`.
- Mock external API calls (Anthropic SDK) using `pytest-mock` — do not make real API requests in tests.

---

## Commit Messages

Use **Conventional Commits** format:

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`

**Examples:**

```
feat(cortex): add memory pruning on conversation limit
fix(chat): resolve SSE stream closing prematurely
docs(readme): update installation steps for Linux
test(prompt_engine): add coverage for placeholder resolution
```

Commit message rules:
- Use the imperative mood in the description ("add", not "added" or "adds").
- Keep the first line under **72 characters**.
- Reference issues where relevant: `Closes #42`.

---

## License

By contributing to PersonaUI you agree that your contributions will be licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**, the same license that covers this project. See [LICENSE](LICENSE) for details.

---

## A Note from the Maintainer

> _"I sincerely apologize for the commit history you may have witnessed during the initial setup of this repository._
> _What you saw was a grown adult repeatedly merging `dev` into `main`, force-pushing, aborting merges, and in one memorable moment, accidentally doing all three at once._
> _I am the person asking **you** to follow Conventional Commits and keep a clean branch structure._
> _The irony is not lost on me._
> _Apparently, writing guidelines about professional Git workflows and actually following them are two completely separate skills — and I am still working on acquiring the latter._
> _We move forward. Cleanly. From now on."_
>
> — The Maintainer, February 2026
