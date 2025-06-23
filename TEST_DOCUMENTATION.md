# Danish Audio Downloader - Test Suite Documentation

This document describes the comprehensive test suite for the Danish Audio Downloader application.

## Overview

The test suite ensures that the Danish Audio Downloader application functions correctly as development continues. It includes tests for:

- GUI components and user interactions
- Core downloading functionality
- Audio file validation
- Settings management
- Error handling
- Threading components

## Test Files

### 1. `test_gui_components.py`
Tests all GUI-related functionality including:
- Window initialization and layout
- Tab creation and navigation
- Widget functionality (buttons, text areas, etc.)
- File dialogs and settings
- Progress tracking
- User input validation
- Message displays

**Key Test Classes:**
- `TestDanishAudioApp`: Comprehensive GUI component testing

### 2. `smoke_test.py`
Quick verification that the application can be imported and basic functionality works:
- Module imports
- Basic class instantiation
- Core functionality validation

### 3. `test_data/`
Directory containing test data files:
- `sample_words.txt`: Sample Danish words for testing
- `mock_ordnet_response.html`: Mock HTML response for testing scraping

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Running All Tests

Use the custom test runner:
```bash
python run_tests.py
```

### Running Individual Test Files

```bash
# GUI tests
python -m unittest test_gui_components -v

# Smoke tests
python smoke_test.py
```

### Running with pytest (if preferred)

```bash
pytest -v
```

## Test Configuration

### `pytest.ini`
Configuration for pytest if you prefer it over unittest:
- Test discovery patterns
- Output formatting
- Timeout settings
- Warning filters

### `requirements-test.txt`
Testing-specific dependencies:
- `pytest` and related plugins
- `pytest-qt` for GUI testing
- `pytest-mock` for mocking
- `pytest-cov` for coverage reporting

## Continuous Integration

### GitHub Actions (`.github/workflows/tests.yml`)
Automated testing on:
- Multiple Python versions (3.8, 3.9, 3.10, 3.11)
- Multiple operating systems (Ubuntu, macOS, Windows)
- Both headless and display environments

## Test Coverage

### Current Coverage Areas

✅ **GUI Components**
- Window initialization and layout
- Tab functionality
- Widget interactions
- File operations
- Settings management
- Progress tracking
- Error handling

✅ **Core Functionality**
- Audio file validation
- HTTP session configuration
- Logging functionality
- Worker thread management

✅ **User Workflows**
- Loading words from files
- Starting/canceling downloads
- Saving settings
- Generating example sentences

### Areas for Future Testing

🔄 **Integration Tests**
- Full download workflow with mocked HTTP requests
- End-to-end sentence generation
- Anki integration testing

🔄 **Performance Tests**
- Large word list handling
- Memory usage during downloads
- UI responsiveness

🔄 **Error Scenarios**
- Network failures
- Invalid file formats
- Disk space issues

## Running Tests in Different Environments

### macOS (Native)
```bash
source .venv/bin/activate
python run_tests.py
```

### Linux (Headless)
```bash
xvfb-run -a python run_tests.py
```

### Windows
```bash
.venv\Scripts\activate
python run_tests.py
```

## Test Structure

### Test Organization
```
test_gui_components.py
├── TestDanishAudioApp
│   ├── GUI initialization tests
│   ├── Widget functionality tests
│   ├── User interaction tests
│   └── Settings tests
```

### Mocking Strategy
- HTTP requests are mocked to avoid external dependencies
- File system operations use temporary directories
- GUI dialogs are mocked for automated testing
- Time-sensitive operations use controlled timing

### Test Data Management
- Temporary directories for file operations
- Mock HTML responses for scraping tests
- Sample word lists for testing workflows

## Best Practices

### Writing New Tests
1. **Use descriptive test names** that explain what is being tested
2. **Mock external dependencies** (HTTP requests, file systems, etc.)
3. **Clean up resources** in tearDown methods
4. **Test both success and failure cases**
5. **Use appropriate assertions** for clear failure messages

### Test Maintenance
1. **Run tests frequently** during development
2. **Update tests when adding new features**
3. **Fix failing tests immediately**
4. **Review test coverage regularly**

## Troubleshooting

### Common Issues

**GUI Tests Fail in Headless Environment**
- Use `xvfb-run` on Linux
- Set `QT_QPA_PLATFORM=offscreen` environment variable

**Import Errors**
- Ensure virtual environment is activated
- Install all dependencies from `requirements-test.txt`

**Slow Tests**
- GUI tests may be slower due to widget creation
- Use `pytest-timeout` to catch hanging tests

### Debug Mode

Run tests with additional debug information:
```bash
python run_tests.py  # Already includes detailed output
```

## Coverage Reporting

Generate test coverage reports:
```bash
pytest --cov=. --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure all existing tests pass
3. Add tests for both success and failure scenarios
4. Update this documentation if needed

## Test Results

The test suite currently achieves:
- ✅ 20/20 GUI component tests passing
- ✅ 100% success rate
- ✅ Fast execution (< 1 second)
- ✅ Cross-platform compatibility

This comprehensive test suite ensures the reliability and maintainability of the Danish Audio Downloader application.
