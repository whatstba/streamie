import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AudioPlayerProvider, useAudioPlayer } from '@/context/AudioPlayerContext'
import { mockTracks, createMockAudioElement, triggerAudioEvent } from '../utils/test-utils'

let mockAudioElement: any

beforeEach(() => {
  mockAudioElement = createMockAudioElement()
  global.Audio = jest.fn(() => mockAudioElement) as any
})

// Simple component that uses the audio player
const TestPlayer = () => {
  const { 
    currentTrack, 
    isPlaying, 
    play, 
    pause, 
    playTrack,
    skipToNext,
    volume,
    setVolume 
  } = useAudioPlayer()
  
  return (
    <div>
      <div data-testid="current-track">{currentTrack?.title || 'No track'}</div>
      <div data-testid="is-playing">{isPlaying ? 'Playing' : 'Paused'}</div>
      <div data-testid="volume">{volume}</div>
      
      <button onClick={() => playTrack(mockTracks[0])}>Load Track 1</button>
      <button onClick={() => playTrack(mockTracks[0], mockTracks)}>Set Queue</button>
      <button onClick={play}>Play</button>
      <button onClick={pause}>Pause</button>
      <button onClick={skipToNext}>Next</button>
      <button onClick={() => setVolume(0.5)}>Set Volume 50%</button>
    </div>
  )
}

describe('Basic Playback Integration', () => {
  it('should handle loading and playing a track', async () => {
    render(
      <AudioPlayerProvider>
        <TestPlayer />
      </AudioPlayerProvider>
    )

    // Initially no track
    expect(screen.getByTestId('current-track')).toHaveTextContent('No track')
    expect(screen.getByTestId('is-playing')).toHaveTextContent('Paused')

    // Load a track
    fireEvent.click(screen.getByText('Load Track 1'))

    // Wait for track to be set
    await waitFor(() => {
      expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
    })

    // Verify audio element setup - the URL is constructed differently
    expect(mockAudioElement.src).toContain('stream')
    expect(mockAudioElement.load).toHaveBeenCalled()

    // Play the track
    fireEvent.click(screen.getByText('Play'))
    expect(mockAudioElement.play).toHaveBeenCalled()

    // Simulate play event
    mockAudioElement.paused = false
    triggerAudioEvent(mockAudioElement, 'play')

    await waitFor(() => {
      expect(screen.getByTestId('is-playing')).toHaveTextContent('Playing')
    })

    // Pause the track
    fireEvent.click(screen.getByText('Pause'))
    expect(mockAudioElement.pause).toHaveBeenCalled()

    mockAudioElement.paused = true
    triggerAudioEvent(mockAudioElement, 'pause')

    await waitFor(() => {
      expect(screen.getByTestId('is-playing')).toHaveTextContent('Paused')
    })
  })

  it('should handle queue and track navigation', async () => {
    render(
      <AudioPlayerProvider>
        <TestPlayer />
      </AudioPlayerProvider>
    )

    // Set queue
    fireEvent.click(screen.getByText('Set Queue'))

    // First track should load automatically
    await waitFor(() => {
      expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
    })

    // Skip to next track
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
    })

    // Verify new audio element setup
    expect(mockAudioElement.src).toContain('stream')
  })

  it('should handle volume control', async () => {
    render(
      <AudioPlayerProvider>
        <TestPlayer />
      </AudioPlayerProvider>
    )

    // Initial volume
    expect(screen.getByTestId('volume')).toHaveTextContent('1')

    // Change volume
    fireEvent.click(screen.getByText('Set Volume 50%'))

    await waitFor(() => {
      expect(screen.getByTestId('volume')).toHaveTextContent('0.5')
    })

    // Verify audio element volume
    expect(mockAudioElement.volume).toBe(0.5)
  })
})