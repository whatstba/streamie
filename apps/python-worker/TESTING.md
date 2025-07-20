# Testing Guide for Python Backend

## Overview

This backend uses pytest for testing with a focus on integration tests for critical functionality. All external dependencies (OpenAI, audio libraries, databases) are mocked to ensure fast, reliable tests.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── integration/          # Integration tests for API flows
│   ├── test_track_analysis.py    # Track analysis & BPM detection
│   ├── test_dj_agent_flow.py     # AI playlist generation
│   ├── test_streaming.py         # Audio file streaming
│   └── test_database_ops.py      # Database operations
├── fixtures/            # Test data and mocks
│   └── mock_data.py    # Mock responses and test data
└── utils/              # Test utilities
    └── helpers.py      # Helper functions
```

## Running Tests

### Using Make commands:
```bash
make test                # Run all tests
make test-integration    # Run integration tests only
make test-coverage      # Run with coverage report
make test-watch         # Run in watch mode
make clean              # Clean test artifacts
```

### Using pytest directly:
```bash
pytest                          # Run all tests
pytest tests/integration/       # Run integration tests
pytest -v -k "test_analyze"     # Run tests matching pattern
pytest --cov=. --cov-report=html  # Generate coverage report
```

## Key Features

### 1. **Synthetic Audio Files**
- Tests use generated audio files instead of real files
- No need for external test data
- Consistent, reproducible tests

### 2. **Mocked External Services**
- OpenAI/LangChain calls are mocked
- Audio analysis libraries (librosa, essentia) are mocked
- Database uses in-memory SQLite for tests

### 3. **Integration Focus**
- Tests complete API flows, not individual functions
- Verifies request/response contracts
- Tests error handling and edge cases

## Test Categories

### Track Analysis Tests
- BPM detection with various audio formats
- Metadata extraction
- Batch analysis
- Caching behavior
- Error handling for corrupted files

### DJ Agent Tests
- Vibe-based playlist generation
- Energy pattern progression
- BPM smooth transitions
- Constraint handling
- Streaming AI responses

### Streaming Tests
- Full file streaming
- HTTP range requests
- Concurrent connections
- Multiple audio formats
- Artwork extraction

### Database Tests
- SQLite adapter MongoDB compatibility
- Track storage and retrieval
- Search functionality
- Transaction handling
- Duplicate prevention

## Fixtures

### Core Fixtures (conftest.py)
- `test_client` - FastAPI test client
- `mock_audio_file` - Single synthetic audio file
- `mock_audio_files` - Multiple audio files with different BPMs
- `mock_db` - Temporary SQLite database
- `mock_openai` - Mocked OpenAI responses
- `mock_langchain` - Mocked LangChain components

### Mock Data (fixtures/mock_data.py)
- Sample track metadata
- Beat tracking responses
- Mood analysis results
- DJ agent responses
- Database entries

## Best Practices

1. **Use Integration Tests**
   - Test complete flows, not isolated functions
   - Mock at the boundary (external services)
   - Keep tests focused on behavior

2. **Mock External Dependencies**
   - Never call real APIs in tests
   - Use consistent mock data
   - Test both success and failure cases

3. **Test Data Management**
   - Use fixtures for reusable test data
   - Clean up after tests (temp files)
   - Keep test data minimal

4. **Async Testing**
   - Use `@pytest.mark.asyncio` for async tests
   - Test streaming endpoints properly
   - Handle async fixtures correctly

## Adding New Tests

1. Choose the right category (integration vs unit)
2. Use existing fixtures when possible
3. Mock external dependencies at the boundary
4. Test both happy path and error cases
5. Keep tests focused and readable

## CI/CD Integration

Tests are designed to run in CI environments:
- No external dependencies required
- Fast execution (mocked I/O)
- Consistent across environments
- Coverage reporting included

## Disabled Endpoints Context

The AI router endpoints (`/ai/*`) are currently disabled in main.py. These provide:
- Advanced vibe analysis
- Intelligent playlist generation
- Track transition rating
- Mixing insights

They were likely disabled during MongoDB→SQLite migration or for API cost management during development.