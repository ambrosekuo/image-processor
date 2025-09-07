# Sprite-Processor Tests

This directory contains comprehensive tests for the sprite-processor package.

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_core.py             # Tests for core functions (remove_bytes, remove_file)
├── test_video.py            # Tests for video processing functions
├── test_api.py              # Tests for API endpoints
├── test_pipeline.py         # Tests for pipeline processing functions
├── test_cli.py              # Tests for CLI functionality
├── test_remove.py           # Legacy tests for backward compatibility
└── README.md               # This file
```

## Test Categories

### Unit Tests
- **Core Functions**: Background removal with different models
- **Video Processing**: Video to GIF, video to spritesheet, video analysis
- **Pipeline Processing**: Video pipeline with single and multiple models
- **CLI Functions**: Command-line interface functionality

### Integration Tests
- **API Endpoints**: Full API testing with FastAPI test client
- **End-to-End Workflows**: Complete processing pipelines

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Basic Test Execution

Run all tests:
```bash
python -m pytest tests/
```

Run specific test modules:
```bash
python -m pytest tests/test_core.py
python -m pytest tests/test_api.py
python -m pytest tests/test_video.py
```

### Using the Test Runner

The `run_tests.py` script provides convenient test execution:

```bash
# Run all tests
python run_tests.py

# Run specific test types
python run_tests.py --type core
python run_tests.py --type api
python run_tests.py --type video

# Run with coverage
python run_tests.py --coverage

# Run in parallel (faster)
python run_tests.py --parallel

# Run only quick tests (exclude slow tests)
python run_tests.py --quick
```

### Test Markers

Tests are marked with categories for selective execution:

```bash
# Run only unit tests
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Exclude slow tests
python -m pytest -m "not slow"
```

## Test Fixtures

The `conftest.py` file provides several useful fixtures:

- `temp_dir`: Temporary directory for test files
- `sample_image`: Sample test image (64x64 with red circle)
- `sample_image_bytes`: Sample image as bytes
- `sample_spritesheet`: 2x2 spritesheet with 4 frames
- `sample_gif`: Animated GIF with 4 frames
- `sample_video_file`: Mock video file for testing
- `mock_rembg_session`: Mock rembg session for testing
- `api_client`: FastAPI test client

## Mocking Strategy

Tests use extensive mocking to avoid dependencies on external services:

- **rembg**: Mocked to avoid downloading models during tests
- **MoviePy**: Mocked to avoid video processing dependencies
- **File I/O**: Uses temporary directories and mock file operations
- **API Calls**: Uses FastAPI test client for API testing

## Coverage

To run tests with coverage reporting:

```bash
python -m pytest --cov=sprite_processor --cov-report=html --cov-report=term
```

This will generate:
- Terminal coverage report
- HTML coverage report in `htmlcov/` directory

## Continuous Integration

The test suite is designed to run in CI environments:

- All external dependencies are mocked
- Tests use temporary directories
- No network calls or external service dependencies
- Fast execution (most tests complete in seconds)

## Adding New Tests

When adding new tests:

1. **Use appropriate fixtures** from `conftest.py`
2. **Mock external dependencies** to keep tests fast and reliable
3. **Add proper docstrings** explaining what each test does
4. **Use descriptive test names** that explain the expected behavior
5. **Group related tests** in classes when appropriate
6. **Add appropriate markers** for test categorization

### Example Test Structure

```python
class TestNewFeature:
    """Test the new feature functionality."""

    def test_new_feature_basic(self, sample_image_bytes):
        """Test basic new feature functionality."""
        # Arrange
        expected_result = "expected"

        # Act
        result = new_feature(sample_image_bytes)

        # Assert
        assert result == expected_result

    def test_new_feature_with_error(self, sample_image_bytes):
        """Test new feature error handling."""
        with pytest.raises(ValueError, match="Invalid input"):
            new_feature(b"invalid data")
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the sprite-processor package is installed in development mode:
   ```bash
   pip install -e .
   ```

2. **Missing Dependencies**: Install test requirements:
   ```bash
   pip install -r requirements-test.txt
   ```

3. **Permission Errors**: Ensure test directories are writable

4. **Slow Tests**: Use markers to exclude slow tests:
   ```bash
   python -m pytest -m "not slow"
   ```

### Debug Mode

Run tests in debug mode for more detailed output:
```bash
python -m pytest -v -s --tb=long
```

## Performance

- **Unit Tests**: < 1 second each
- **Integration Tests**: 1-5 seconds each
- **Full Test Suite**: < 30 seconds
- **With Coverage**: < 60 seconds

The test suite is optimized for speed while maintaining comprehensive coverage.
