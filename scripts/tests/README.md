# Tests

Unit and integration tests for the backlog manager system.

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest scripts/tests/test_state.py
pytest scripts/tests/test_issue_helpers.py
pytest scripts/tests/test_document_loader.py
```

### Run Specific Test Class

```bash
pytest scripts/tests/test_issue_helpers.py::TestNormalizeIssueBody
pytest scripts/tests/test_issue_helpers.py::TestCategorizeIssueToMilestone
```

### Run Specific Test Function

```bash
pytest scripts/tests/test_state.py::test_backlog_state_initialization
pytest scripts/tests/test_issue_helpers.py::TestNormalizeIssueBody::test_plain_text_body
```

### Run with Coverage

```bash
pytest --cov=backlog --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Only Specific Markers

```bash
pytest -m unit
pytest -m integration
pytest -m "unit or integration"
```

## Test Structure

- `test_state.py` - Tests for BacklogState data structure
- `test_issue_helpers.py` - Tests for issue processing helper functions
- `test_document_loader.py` - Tests for document loading functionality
- `conftest.py` - Shared fixtures and pytest configuration

## Test Coverage

This test suite covers:

### BacklogState Tests
- State initialization
- Data population
- Error tracking
- Required keys validation

### Issue Helper Tests
- Issue body normalization (plain text, dict, empty, whitespace)
- Issue categorization to milestones
- Sprint label assignment and cycling
- Case-insensitive keyword matching

### Document Loader Tests
- Document loading patterns
- Path handling (relative paths, README special handling)
- Documentation structure validation

## Fixtures Available

Tests can use the following fixtures from `conftest.py`:

- `sample_backlog_state` - A populated BacklogState for testing
- `sample_issue` - A sample GitHub issue structure
- `sample_docs_content` - Sample documentation content
- `temp_workspace` - A temporary workspace with docs structure
- `mock_github_issue` - A mock GitHub API response

Example:
```python
def test_with_fixture(sample_backlog_state):
    assert sample_backlog_state["published_issue_numbers"] == [1, 2]
```

## Adding New Tests

1. Create test function with `test_` prefix in appropriate file
2. Use fixtures by adding them as parameters
3. Use assertions to verify behavior
4. Group related tests in Test classes for organization

Example:
```python
def test_new_feature(sample_issue):
    """Test description"""
    result = function_to_test(sample_issue)
    assert result == expected_value
```

## CI/CD Integration

To run tests in CI/CD:

```yaml
- name: Run tests
  run: pytest --cov=backlog --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```
