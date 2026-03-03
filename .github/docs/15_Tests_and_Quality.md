# 15 — Tests & Quality

> Comprehensive test suite with pytest, fixtures, mocking, and quality tools.

---

## Overview

PersonaUI has a robust test architecture with **pytest** covering **362+ tests** across **16 test files** (~5,600 lines of test code). All tests run completely isolated without real API calls, database connections, or file system modifications — everything is mocked for fast, reliable execution.

```
src/tests/
├── conftest.py                              Shared fixtures & setup (11 fixtures)
├── test_api_client.py                       API client & data types (23 tests)
├── test_provider.py                         Service provider pattern (6 tests)
├── test_health_endpoint.py                  Health check route (4 tests)
├── test_version_info.py                     Version info utility (6 tests)
├── test_integration/
│   ├── test_afterthought_flow.py            E2E afterthought workflow (2 tests)
│   ├── test_chat_flow.py                    E2E chat conversation (12 tests)
│   └── test_step06_api_integration.py       App startup & wiring (32 tests)
├── test_prompt_engine/
│   ├── test_prompt_engine.py                Core prompt engine (59 tests)
│   ├── test_phase5.py                       Export/Import/Reset (19 tests)
│   └── test_step04_cortex_prompts.py        Cortex prompts & placeholders (47 tests)
└── test_services/
    ├── test_chat_service.py                 Chat service layer (9 tests)
    ├── test_cortex_service.py               Cortex service core (28 tests)
    ├── test_cortex_service_robustness.py    Atomic writes & hardening (16 tests)
    ├── test_cortex_tiers.py                 Tier tracking & checking (25 tests)
    ├── test_cortex_update_service.py        Cortex update workflows (21 tests)
    └── test_tool_request.py                 Tool use & loops (18 tests)
```

---

## Configuration

### pytest.ini

```ini
[pytest]
testpaths = src/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### Running Tests

```bash
# All tests (from project root)
cd /home/sakushi/projekt/personaui
pytest

# Specific test file
pytest src/tests/test_version_info.py

# Specific test pattern
pytest -k "test_version"

# With verbose output
pytest -v

# With coverage (requires pytest-cov)
pytest --cov=src

# Stop on first failure
pytest -x

# Run only failed tests from last run
pytest --lf
```

---

## Fixtures & Test Infrastructure

### conftest.py — Shared Fixtures

**File:** `src/tests/conftest.py` (194 lines)

Provides 11 shared fixtures used across all test files:

#### Character & Persona Data

```python
@pytest.fixture
def test_character_data():
    """Standard test persona with complete character data."""
    return {
        'char_name': 'TestPersona',
        'desc': 'Eine Test-Persona für Unit-Tests.',
        'start_msg_enabled': True,
        'background': 'TestPersona wurde in einer kleinen Stadt geboren.',
        'identity': 'TestPersona, 25, weiblich',
        'example_dialogue': '{{user}}: Hallo!\n{{char}}: *lächelt warmherzig* Hallo!'
        # ... complete persona structure
    }

@pytest.fixture
def mock_persona_config():
    """Mock persona configuration with all required fields."""
    
@pytest.fixture 
def sample_prompts():
    """Sample prompt templates for testing."""
```

#### API & Service Mocks

```python
@pytest.fixture
def mock_api_client():
    """Fully mocked ApiClient that never makes real HTTP calls."""
    
@pytest.fixture
def mock_chat_service():
    """ChatService with mocked database interactions."""
    
@pytest.fixture
def mock_cortex_service():
    """CortexService with mocked file operations."""
```

#### Database & File System

```python
@pytest.fixture
def temp_db():
    """In-memory SQLite database for testing."""
    
@pytest.fixture
def temp_cortex_dir(tmp_path):
    """Temporary directory for cortex file operations."""

@pytest.fixture
def mock_settings():
    """Mock settings that don't touch real config files."""
```

#### Environment Setup

```python
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Sets up the test environment before any tests run."""
    # Changes working directory to src/
    # Ensures imports work correctly
    # Prevents side effects on real application
```

### Key Testing Principles

1. **No Side Effects**: Tests never modify real files, databases, or make HTTP calls
2. **Isolated**: Each test gets fresh fixtures and can run independently
3. **Fast**: Full test suite runs in under 10 seconds
4. **Deterministic**: No random failures or timing dependencies

---

## Test Categories

### Core API & Clients — `test_api_client.py`

**23 tests** covering the HTTP client layer:

- **API Client**: Connection handling, request/response parsing
- **Data Types**: Validation of API response structures
- **Error Handling**: Network failures, invalid responses, timeouts
- **Mock Integration**: Ensures no real API calls during testing

```python
def test_api_client_chat_completion(mock_api_client):
    """Test chat completion with mocked response."""
    
def test_api_response_validation():
    """Test API response data type validation."""
    
def test_network_error_handling(mock_api_client):
    """Test graceful handling of network failures."""
```

### Service Provider — `test_provider.py`

**6 tests** for the service locator pattern:

- **Singleton Behavior**: Services are created once and reused
- **Service Registration**: Proper initialization and dependency injection
- **Service Resolution**: Getter functions return correct instances

```python
def test_provider_singleton():
    """Test that provider returns same instance."""
    
def test_service_initialization():
    """Test proper service setup and wiring."""
```

### Version Utility — `test_version_info.py`

**6 tests** for the version information utility:

- **Valid JSON**: Reading and parsing version.json correctly
- **Missing File**: Graceful fallback when version.json doesn't exist
- **Invalid JSON**: Error handling for malformed JSON
- **Caching**: Module-level caching works correctly
- **Version Formats**: Various version string formats (1.2.3, 1.2.3-alpha)
- **Missing Keys**: Fallback when version key is missing

```python
def test_valid_version_json():
    """Test reading valid version.json file."""
    
def test_caching():
    """Test that result is cached (same object returned)."""
    
def test_version_formats():
    """Test various version string formats."""
```

### Health Check — `test_health_endpoint.py`

**4 tests** for the health monitoring endpoint:

- **Basic Health**: Simple health check response
- **Status Codes**: Proper HTTP status codes
- **Response Format**: JSON structure validation
- **Error Conditions**: Health check failures

---

## Integration Tests

### Chat Flow — `test_chat_flow.py`

**12 tests** for end-to-end chat conversations:

- **Full Conversation**: User message → AI response → database storage
- **Message History**: Retrieving and formatting conversation history  
- **Character Integration**: Persona-specific responses and behavior
- **Error Recovery**: Handling API failures during chat

```python
def test_complete_chat_flow(mock_api_client, temp_db):
    """Test full chat conversation from user input to stored response."""
    
def test_chat_history_retrieval():
    """Test loading and formatting conversation history."""
    
def test_persona_integration():
    """Test that persona settings affect chat behavior."""
```

### Afterthought Flow — `test_afterthought_flow.py`

**2 tests** for the afterthought feature:

- **Afterthought Generation**: Creating follow-up thoughts
- **Integration**: Afterthoughts in context of conversation

### Application Integration — `test_step06_api_integration.py`

**32 tests** for application startup and service wiring:

- **App Initialization**: Flask app creation and configuration
- **Service Setup**: All services properly initialized and connected
- **Database Migration**: Schema creation and migration handling
- **Route Registration**: All blueprints and endpoints registered
- **Error Handling**: Startup failures and recovery

```python
def test_app_initialization():
    """Test Flask app creates successfully with all services."""
    
def test_database_migration():
    """Test database schema creation and migration."""
    
def test_route_registration():
    """Test all routes are properly registered."""
```

---

## Prompt Engine Tests

### Core Engine — `test_prompt_engine.py`

**59 tests** for the prompt generation system:

- **Template Loading**: Reading and parsing prompt templates
- **Placeholder Resolution**: Dynamic variable substitution
- **Context Building**: Chat history and persona integration  
- **Template Validation**: Syntax checking and error handling
- **Performance**: Template caching and optimization

```python
def test_template_loading():
    """Test loading prompt templates from files."""
    
def test_placeholder_resolution():
    """Test {{variable}} substitution works correctly."""
    
def test_context_building():
    """Test building full prompt context from chat history."""
```

### Export/Import/Reset — `test_phase5.py`

**19 tests** for data management operations:

- **Export**: Complete persona and chat data export
- **Import**: Restoring from exported data
- **Reset**: Clean slate functionality
- **Data Integrity**: Ensuring no data corruption during operations

### Cortex Integration — `test_step04_cortex_prompts.py`

**47 tests** for Cortex memory system integration:

- **Memory Integration**: Cortex data in prompt context
- **Dynamic Updates**: Real-time memory updates during conversations
- **Placeholder Processing**: Cortex-specific template variables
- **Performance**: Memory system performance with large datasets

---

## Service Layer Tests

### Chat Service — `test_chat_service.py`

**9 tests** for the chat business logic layer:

- **Message Processing**: Cleaning and formatting user input
- **Response Generation**: Coordinating with API client and prompt engine
- **Database Operations**: Message storage and retrieval
- **Error Handling**: API failures, database errors

### Cortex Services

#### Core Service — `test_cortex_service.py` (28 tests)

- **Memory Operations**: Creating, updating, retrieving memories
- **File Management**: Cortex file organization and access
- **Data Validation**: Memory content validation and sanitization

#### Robustness — `test_cortex_service_robustness.py` (16 tests)

- **Atomic Operations**: Ensuring data consistency during updates
- **Concurrent Access**: Multiple simultaneous operations
- **Error Recovery**: Handling partial failures and rollbacks
- **Cache Management**: Memory caching and invalidation

#### Tier Management — `test_cortex_tiers.py` (25 tests)

- **Tier Assignment**: Automatic memory importance classification
- **Tier Transitions**: Moving memories between tiers
- **Storage Optimization**: Efficient storage based on importance
- **Cleanup Operations**: Removing old or irrelevant memories

#### Update Service — `test_cortex_update_service.py` (21 tests)

- **Memory Updates**: Modifying existing memories
- **Conflict Resolution**: Handling conflicting memory updates
- **Versioning**: Memory version tracking and history
- **Synchronization**: Keeping multiple memory sources in sync

### Tool Request Processing — `test_tool_request.py`

**18 tests** for tool use and workflow loops:

- **Tool Execution**: Running tools and capturing results
- **Loop Detection**: Preventing infinite tool chains
- **Error Handling**: Tool failures and recovery
- **Result Integration**: Incorporating tool results into responses

---

## Quality Tools & Standards

### Code Style

The project uses Python's built-in standards with pytest-specific conventions:

- **Naming**: Test functions start with `test_`, classes with `Test`
- **Structure**: Arrange-Act-Assert pattern in all tests
- **Fixtures**: Prefer fixtures over setUp/tearDown methods
- **Assertions**: Use pytest's assert with clear failure messages

### Frontend Testing

**File:** `frontend/.eslintrc.js`

```javascript
module.exports = {
  extends: [
    'react-app',
    'react-app/jest'
  ],
  rules: {
    'no-unused-vars': 'warn',
    'react/prop-types': 'off'
  }
};
```

### Test Data Management

- **Fixtures**: All test data defined in conftest.py
- **Factories**: Helper functions for creating test objects
- **Mocking**: unittest.mock for external dependencies
- **Isolation**: Each test gets fresh data and clean state

### Performance Guidelines

- **Fast Tests**: Full suite under 10 seconds
- **Parallel Safe**: Tests can run concurrently
- **Resource Light**: Minimal memory and disk usage
- **Deterministic**: No flaky or timing-dependent tests

---

## Running Different Test Suites

### Development Workflow

```bash
# Quick smoke test (critical paths only)
pytest src/tests/test_integration/test_step06_api_integration.py

# Full backend test
pytest src/tests/ -v

# Test specific feature
pytest -k "cortex" -v

# Test with coverage
pytest --cov=src --cov-report=html

# Performance testing
pytest --benchmark-only  # (if pytest-benchmark installed)
```

### CI/CD Pipeline

```bash
# Production readiness check
pytest src/tests/ --tb=short -q

# With strict warnings
pytest src/tests/ -W error

# JUnit XML output for CI
pytest src/tests/ --junitxml=test-results.xml
```

### Debugging Failed Tests

```bash
# Stop on first failure with full traceback
pytest -x --tb=long

# Run only failed tests from last run
pytest --lf -v

# Run specific failing test with detailed output
pytest src/tests/test_api_client.py::test_specific_function -v -s
```

---

## Mock Strategy

### API Mocking

All external HTTP calls are mocked:

```python
# Anthropic Claude API
@pytest.fixture
def mock_anthropic_response():
    return {
        "content": [{"text": "Mocked AI response"}],
        "role": "assistant",
        "stop_reason": "end_turn"
    }
```

### Database Mocking

In-memory SQLite for all database tests:

```python
@pytest.fixture
def temp_db():
    """Creates fresh in-memory database for each test."""
    db = sqlite3.connect(':memory:')
    # Load schema and return connection
```

### File System Mocking

Temporary directories for file operations:

```python
@pytest.fixture
def temp_cortex_dir(tmp_path):
    """Temporary cortex directory that auto-cleans."""
    return tmp_path / "cortex"
```

---

## Test Coverage Areas

### ✅ Full Coverage

- **API Client Layer**: All HTTP operations
- **Service Provider**: Dependency injection
- **Prompt Engine**: Template processing
- **Database Operations**: All CRUD operations
- **Utility Functions**: Helpers and formatters

### 🔄 Partial Coverage

- **Frontend Components**: Basic ESLint only
- **WebView Integration**: Manual testing only
- **Error Logging**: Core paths covered

### 📋 Not Covered

- **Real API Integration**: Only mocked calls tested
- **Browser Compatibility**: Manual testing required
- **Performance Under Load**: Manual stress testing

---

## Adding New Tests

### Test File Structure

```python
"""
Test module docstring explaining what's being tested.
"""
import pytest
# Standard test imports...

class TestFeatureName:
    """Test class for logical grouping."""
    
    def test_basic_functionality(self, fixture_name):
        """Test basic feature behavior."""
        # Arrange
        input_data = create_test_data()
        
        # Act  
        result = feature.process(input_data)
        
        # Assert
        assert result.success == True
        assert result.data == expected_data
    
    def test_error_conditions(self):
        """Test error handling."""
        with pytest.raises(SpecificException):
            feature.process(invalid_data)
```

### Best Practices

1. **One Concept Per Test**: Each test should verify one specific behavior
2. **Clear Test Names**: Test name should describe what's being verified
3. **Arrange-Act-Assert**: Structure all tests with clear sections
4. **Use Fixtures**: Share setup code via fixtures, not helpers
5. **Mock External**: Mock anything outside the current module
6. **Fast Execution**: Keep tests under 100ms each

---

## Related Documentation

- [08 — Database Layer](08_Database_Layer.md) — Database testing strategies
- [11 — Services Layer](11_Services_Layer.md) — Service mocking patterns
- [06 — Prompt Engine](06_Prompt_Engine.md) — Template testing approach
- [01 — App Core](01_App_Core_and_Startup.md) — Integration test coverage
