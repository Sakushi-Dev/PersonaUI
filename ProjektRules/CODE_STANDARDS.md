# PersonaUI Code Standards & Development Guidelines

> **Philosophy:** Clean, maintainable, and human-friendly. Less is more - clear standards everyone can follow.

## 🏗️ Branch Strategy

### Branch Purpose

- **`main`** - Stable Release Branch
  - Only tested, fully functional features
  - Direct pushes forbidden - merges only via PR
  - Every merge = potential release

- **`dev`** - Development Integration Branch
  - Active development of all features
  - Integration testing before main
  - Collection point for all feature branches

- **`redesign`** - Focused Refactoring Branch
  - **Goal-oriented:** One area at a time (e.g. Frontend Refactor with React/Node.js)
  - Structured modernization, never "everything at once"
  - Merge to `dev` when milestone is reached

### Workflow

```
feature/xyz → dev → main
redesign → dev → main (at milestones)
hotfix → main (+ cherry-pick to dev)
```

**Merge Rule:** Frontend first → then Backend → then Integration

---

## 💻 Code Standards

### Python (Backend)

#### Naming Conventions
```python
# Classes: PascalCase
class ApiClient:
class DatabaseManager:

# Functions/Variables: snake_case
def get_user_data():
def api_key_valid():

# Constants: UPPER_SNAKE_CASE
API_BASE_URL = "https://api.anthropic.com"
DEFAULT_TIMEOUT = 30

# Private: _leading_underscore
def _internal_helper():
self._private_var = value
```

#### Function Structure
```python
def process_user_message(message: str, persona_id: int = None) -> dict:
    """
    Short description of what the function does.

    Args:
        message: Incoming message from the user
        persona_id: Optional - which persona to use

    Returns:
        Dict with processed message and metadata

    Raises:
        ValueError: On invalid persona_id
    """
    # Implementation...
    return {"processed": message, "persona": persona_id}
```

#### Error Handling
```python
# Good: Specific exceptions
try:
    result = api_call()
except requests.RequestException as e:
    logger.error(f"API request failed: {e}")
    return {"error": "API temporarily unavailable"}

# Bad: Bare except
try:
    result = dangerous_operation()
except:  # NEVER!
    pass
```

### JavaScript/React (Frontend)

#### Naming Conventions
```javascript
// Components: PascalCase
const MessageBubble = () => {};
const UserProfileOverlay = () => {};

// Functions/Variables: camelCase
const handleSubmit = () => {};
const isAuthenticated = false;

// Constants: UPPER_SNAKE_CASE
const API_ENDPOINTS = {
  CHAT: "/api/chat",
  USER: "/api/user"
};

// Props: Descriptive names
const MessageList = ({ messages, onMessageSend, isLoading }) => {};
```

#### Component Structure
```jsx
// Imports grouped
import React, { useState, useEffect, useCallback } from 'react';
import Button from '../../components/Button/Button';
import { sendMessage } from '../../services/chatApi';
import styles from './MessageBubble.module.css';

// Props as destructured parameter
export default function MessageBubble({
  message,
  isOwn = false,
  onReply
}) {
  // State hooks first
  const [isEditing, setIsEditing] = useState(false);

  // Effect hooks
  useEffect(() => {
    // Side effects
  }, [message.id]);

  // Event handlers as useCallback
  const handleEdit = useCallback(() => {
    setIsEditing(true);
  }, []);

  // Early returns
  if (!message) return null;

  // Render logic
  return (
    <div className={`${styles.bubble} ${isOwn ? styles.own : ''}`}>
      {/* JSX */}
    </div>
  );
}
```

#### CSS Module Standards
```css
/* FileName.module.css */

/* Container first */
.container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Elements alphabetically */
.button {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

/* Modifiers with base class */
.button.primary {
  background: var(--color-primary);
  color: white;
}

/* States */
.button:hover {
  transform: translateY(-1px);
}

/* Media queries at the end */
@media (max-width: 768px) {
  .container {
    gap: 12px;
  }
}
```

---

## 🔄 Refactoring Guidelines

### The "Focused Refactor" Rule
1. **One goal per session** - never refactor everything at once
2. **Tests first** - existing tests must keep passing
3. **Small steps** - many small commits instead of massive changes
4. **Document intent** - why is this being refactored?

### Refactor Priorities
```
1. Security Issues (immediate)
2. Performance Bottlenecks (high)
3. Code Duplication (medium)
4. Styling/Structure (low)
```

### Refactor Commit Pattern
```bash
# Good
git commit -m "refactor: extract user auth logic to separate service

- Move authentication logic from multiple components to authService.js
- Reduces code duplication across UserProfile and LoginForm
- No functional changes, maintains existing API"

# Bad
git commit -m "cleanup stuff"
```

---

## 📝 Comment Standards

### Python Comments
```python
class MessageProcessor:
    """
    Processes incoming user messages and prepares them for API calls.

    Handles message sanitization, persona selection, and API formatting.
    """

    def __init__(self, default_persona: str = "assistant"):
        # Store default persona for fallback cases
        self.default_persona = default_persona

    def process(self, raw_message: str) -> dict:
        # TODO: Add support for message attachments (#123)
        # FIXME: Handle edge case with empty messages (#456)

        # Sanitize user input before processing
        clean_message = self._sanitize(raw_message)

        return {"message": clean_message}
```

### JavaScript Comments
```javascript
/**
 * Custom hook for managing chat message state and API calls.
 *
 * @param {string} chatId - Unique identifier for the chat session
 * @returns {Object} Message state and handler functions
 */
function useMessages(chatId) {
  // Track loading state separately from message data
  // to prevent UI flicker during sends
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (content) => {
    // TODO: Add message queuing for offline mode
    // Optimistic update - show message immediately
    setMessages(prev => [...prev, { content, status: 'sending' }]);

    try {
      const result = await chatApi.send(content);
      updateMessage(result.id, { status: 'sent', ...result });
    } catch (error) {
      // FIXME: Better error handling needed here
      console.error('Send failed:', error);
    }
  }, [chatId]);
}
```

### Comment Rules
- **Why, not what** - code shows what happens, comments explain why
- **TODO/FIXME with issue number** - trackable action items
- **Explain complex logic** - non-obvious algorithms deserve context
- **Document API changes** - highlight breaking changes

---

## 📦 Commit Standards

### Commit Message Format
```
type(scope): brief description

Optional longer explanation of what and why vs. how.

Breaking changes noted here.
Closes #issue-number
```

### Types
- **feat:** New functionality
- **fix:** Bug fix
- **refactor:** Code restructuring without functional changes
- **style:** Formatting, missing semicolons, etc.
- **docs:** Documentation
- **test:** Adding/changing tests
- **chore:** Build process, dependencies, etc.

### Examples
```bash
# New feature
git commit -m "feat(chat): add message reactions with emoji picker

- Users can now react to messages with emojis
- Reactions stored per-user and synced real-time
- Includes hover animations and accessibility support

Closes #234"

# Bug fix
git commit -m "fix(api): handle connection timeout gracefully

- Catch timeout exceptions in api_client.py
- Show user-friendly error instead of crash
- Add retry mechanism with exponential backoff

Fixes #456"

# Refactoring
git commit -m "refactor(overlays): consolidate duplicate modal logic

- Extract common modal behavior to BaseOverlay component
- Reduces code duplication across 8 overlay components
- No functional changes to user-facing behavior"
```

---

## 📁 File Organization

### Frontend Structure
```
frontend/src/
├── components/          # Reusable UI components
│   ├── Button/
│   ├── Modal/
│   └── FormGroup/
├── features/           # Feature-specific code
│   ├── chat/
│   ├── overlays/
│   └── onboarding/
├── services/           # API clients, external services
├── hooks/              # Custom React hooks
├── utils/              # Pure utility functions
└── styles/             # Global styles, themes
```

### Backend Structure
```
src/
├── routes/            # Flask route handlers
├── utils/             # Utility modules
│   ├── api_request/   # API client logic
│   ├── database/      # Database operations
│   └── helpers.py     # General helpers
├── templates/         # Jinja2 templates
├── sql/               # Database schemas
└── tests/             # Test files mirror src structure
```

### Naming Rules
- **Files:** lowercase_with_underscores.py, PascalCase.jsx
- **Directories:** lowercase, descriptive
- **Assets:** descriptive names, version if needed (logo_v2.png)

---

## 🧪 Testing Standards

### Test Coverage Goals
- **Critical Paths:** 100% coverage (user auth, API calls)
- **Business Logic:** 90% coverage
- **UI Components:** 70% coverage
- **Utilities:** 95% coverage

### Python Tests
```python
# tests/test_api_client.py
import pytest
from unittest.mock import patch, Mock
from src.utils.api_request.client import ApiClient

class TestApiClient:
    """Test suite for API client functionality."""

    def setup_method(self):
        """Setup run before each test method."""
        self.client = ApiClient(api_key="test-key")

    def test_send_message_success(self):
        """Test successful message sending."""
        # Arrange
        test_message = "Hello AI"

        # Act
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {"response": "Hi!"}
            result = self.client.send_message(test_message)

        # Assert
        assert result["response"] == "Hi!"
        mock_post.assert_called_once()

    def test_send_message_api_error(self):
        """Test handling of API errors."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.RequestException("Connection failed")

            with pytest.raises(ApiClientError):
                self.client.send_message("test")
```

### React Tests
```jsx
// MessageBubble.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import MessageBubble from '../MessageBubble';

describe('MessageBubble', () => {
  const defaultProps = {
    message: { id: 1, content: "Hello", sender: "user" },
    onReply: jest.fn()
  };

  it('renders message content', () => {
    render(<MessageBubble {...defaultProps} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('calls onReply when reply button clicked', () => {
    render(<MessageBubble {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /reply/i }));
    expect(defaultProps.onReply).toHaveBeenCalledWith(defaultProps.message);
  });

  it('applies own message styling for user messages', () => {
    render(<MessageBubble {...defaultProps} isOwn={true} />);
    const bubble = screen.getByTestId('message-bubble');
    expect(bubble).toHaveClass('own');
  });
});
```

---

## 👥 Code Review Process

### Review Checklist
- [ ] **Functionality:** Does it work as intended?
- [ ] **Tests:** Are there appropriate tests?
- [ ] **Performance:** Any obvious bottlenecks?
- [ ] **Security:** Input validation, XSS prevention?
- [ ] **Style:** Follows project conventions?
- [ ] **Documentation:** Complex logic explained?

### Review Guidelines
- **Be constructive** - suggest solutions, not just problems
- **Focus on code, not coder** - "This function could be simpler" not "You wrote bad code"
- **Explain reasoning** - why is a change needed?
- **Approve small changes quickly** - don't block obvious fixes

### Pull Request Template
```markdown
## What Changed
Brief description of the change and why it was needed.

## Testing Done
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] Cross-browser testing (if UI changes)

## Breaking Changes
List any breaking changes and migration steps.

## Screenshots
If UI changes, include before/after screenshots.

## Checklist
- [ ] Code follows project standards
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No console errors
```

---

## 🔧 Development Tools & Scripts

### Build Scripts
```bash
# Frontend Development
cd frontend/
npm install          # Install dependencies
npm run dev          # Start dev server
npm run build        # Production build
npm run test         # Run tests
npm run lint         # Lint code

# Backend Development
python -m pytest     # Run tests
python -m flake8 src # Lint Python
python src/app.py    # Start dev server

# Frontend Build (from project root)
# Windows: src/dev/frontend/build_frontend.bat
# Linux:   src/dev/frontend/build_frontend.sh
```

---

## 📖 Quick Reference

### Common Patterns
```python
# API Error Handling
try:
    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    return response.json()
except requests.RequestException as e:
    logger.error(f"API request failed: {e}")
    raise ApiError(f"Request failed: {str(e)}")

# Database Operations
def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user data by ID, returns None if not found."""
    cursor = get_db_cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
```

```jsx
// API Calls with Error Handling
const useApiCall = (url, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [url]);

  return { data, loading, error, execute };
};
```

---

## 🚀 Deployment & Release

### Release Process
1. **Feature Complete** in `dev` branch
2. **Integration Testing** - all features work together
3. **Merge to main** via Pull Request
4. **Tag Release** - `git tag v1.2.3`
5. **Deploy** - automated or manual
6. **Monitor** - check logs and user feedback

### Version Numbering
```
MAJOR.MINOR.PATCH
1.2.3

MAJOR - Breaking changes (API changes)
MINOR - New features (backwards compatible)
PATCH - Bug fixes
```

---

**📝 Document Version:** 1.0
**Created:** 2026-02-19
**Purpose:** Pragmatic standards for clean, maintainable PersonaUI code

> These standards are living documents - they evolve with the project. Feedback and improvements always welcome!
