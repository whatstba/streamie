import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AudioPlayerProvider, useAudioPlayer } from '@/context/AudioPlayerContext'
import { mockTracks, createMockAudioElement } from '../utils/test-utils'

let mockAudioElement: any
let mockAudioContext: any

beforeEach(() => {
  mockAudioElement = createMockAudioElement()
  global.Audio = jest.fn(() => mockAudioElement) as any
  
  // Simple mock for AudioContext
  mockAudioContext = {
    createGain: jest.fn(() => ({
      gain: { value: 1 },
      connect: jest.fn(),
      disconnect: jest.fn(),
    })),
    createMediaElementSource: jest.fn(() => ({
      connect: jest.fn(),
      disconnect: jest.fn(),
    })),
    destination: {},
  }
  
  global.AudioContext = jest.fn(() => mockAudioContext) as any
})

// Test component for DJ mode
const TestDjMode = () => {
  const { 
    djMode,
    toggleDjMode,
    setCrossfadeDuration,
    setTransitionTime,
    isTransitioning,
    transitionProgress,
    currentTrack,
    playTrack
  } = useAudioPlayer()
  
  React.useEffect(() => {
    // Start playing the first track with the full queue
    if (mockTracks.length > 0) {
      playTrack(mockTracks[0], mockTracks)
    }
  }, [playTrack])
  
  return (
    <div>
      <div data-testid="dj-enabled">{djMode ? 'Enabled' : 'Disabled'}</div>
      <div data-testid="is-transitioning">{isTransitioning ? 'Yes' : 'No'}</div>
      <div data-testid="transition-progress">{transitionProgress}</div>
      <div data-testid="current-track">{currentTrack?.title || 'No track'}</div>
      
      <button onClick={toggleDjMode}>Toggle DJ Mode</button>
      <button onClick={() => setCrossfadeDuration(10)}>Set Crossfade 10s</button>
      <button onClick={() => setTransitionTime(45)}>Set Transition 45s</button>
    </div>
  )
}

describe('DJ Mode Basic Integration', () => {
  it('should toggle DJ mode and update settings', async () => {
    render(
      <AudioPlayerProvider>
        <TestDjMode />
      </AudioPlayerProvider>
    )

    // Wait for queue to load
    await waitFor(() => {
      expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
    })

    // Initially DJ mode is off
    expect(screen.getByTestId('dj-enabled')).toHaveTextContent('Disabled')

    // Enable DJ mode
    fireEvent.click(screen.getByText('Toggle DJ Mode'))

    await waitFor(() => {
      expect(screen.getByTestId('dj-enabled')).toHaveTextContent('Enabled')
    })

    // Update crossfade duration
    fireEvent.click(screen.getByText('Set Crossfade 10s'))

    // Update transition time
    fireEvent.click(screen.getByText('Set Transition 45s'))

    // Verify AudioContext was created
    expect(global.AudioContext).toHaveBeenCalled()
  })

  it('should show transition state', async () => {
    render(
      <AudioPlayerProvider>
        <TestDjMode />
      </AudioPlayerProvider>
    )

    // Initially not transitioning
    expect(screen.getByTestId('is-transitioning')).toHaveTextContent('No')
    expect(screen.getByTestId('transition-progress')).toHaveTextContent('0')

    // Note: Actually triggering transitions would require more complex mocking
    // of timers and audio playback, which is better suited for E2E tests
  })
})