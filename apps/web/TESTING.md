# Testing Guide for Streamie Web App

## Overview

This project uses Jest and React Testing Library for testing the web application. The testing strategy focuses on integration tests for critical user flows rather than brittle unit tests.

## Test Structure

```
__tests__/
├── integration/        # Integration tests for user flows
├── utils/             # Test utilities and helpers
└── setup.test.tsx     # Verification that test setup works
```

## Running Tests

```bash
npm test              # Run all tests
npm test:watch       # Run tests in watch mode
npm test:coverage    # Run tests with coverage report
npm test:ci          # Run tests in CI mode
```

## Key Test Files

### Integration Tests
- `BasicPlayback.test.tsx` - Core audio playback functionality
- `DjModeBasic.test.tsx` - DJ mode features and transitions
- `QueueBasic.test.tsx` - Queue management operations

### Test Utilities
- `test-utils.tsx` - Custom render functions and mock data
- `mockAudioContext.ts` - Web Audio API mocks

## Testing Approach

1. **Integration over Unit Tests** - Focus on testing complete user flows
2. **Mock External Dependencies** - Audio elements and Web Audio API are mocked
3. **Test State Management** - Verify AudioPlayerContext state changes
4. **No Real Audio** - Tests verify state management, not actual audio output

## Example Test Pattern

```typescript
// Render component with AudioPlayerProvider
render(
  <AudioPlayerProvider>
    <YourComponent />
  </AudioPlayerProvider>
)

// Interact with the UI
fireEvent.click(screen.getByText('Play'))

// Verify state changes
await waitFor(() => {
  expect(screen.getByTestId('is-playing')).toHaveTextContent('Playing')
})
```

## Mocked APIs

- `HTMLAudioElement` - Play, pause, load, and events
- `AudioContext` - Web Audio API nodes and connections
- `IntersectionObserver` - For virtualized components

## Future Improvements

1. Add E2E tests with Playwright for complete user journeys
2. Add visual regression tests for UI components
3. Mock backend API responses with MSW
4. Add performance tests for large playlists
5. Test error scenarios and edge cases