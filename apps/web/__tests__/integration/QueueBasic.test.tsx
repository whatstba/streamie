import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { AudioPlayerProvider, useAudioPlayer } from '@/context/AudioPlayerContext'
import { mockTracks } from '../utils/test-utils'

// Test component for queue management
const TestQueue = () => {
  const { 
    queue,
    currentTrack,
    addToQueue,
    removeFromQueue,
    clearQueue,
    playTrack,
    moveQueueItem
  } = useAudioPlayer()
  
  return (
    <div>
      <div data-testid="queue-length">{queue.length}</div>
      <div data-testid="current-track">{currentTrack?.title || 'No track'}</div>
      <div data-testid="queue-items">
        {queue.map((track, index) => (
          <div key={track.id} data-testid={`track-${index}`}>
            {track.title}
          </div>
        ))}
      </div>
      
      <button onClick={() => playTrack(mockTracks[0], mockTracks)}>Set Initial Queue</button>
      <button onClick={() => addToQueue(mockTracks[0])}>Add Track 1</button>
      <button onClick={() => removeFromQueue(1)}>Remove Index 1</button>
      <button onClick={() => moveQueueItem(0, 2)}>Move First to Third</button>
      <button onClick={clearQueue}>Clear Queue</button>
    </div>
  )
}

describe('Queue Management Integration', () => {
  it('should handle queue operations', async () => {
    render(
      <AudioPlayerProvider>
        <TestQueue />
      </AudioPlayerProvider>
    )

    // Initially empty
    expect(screen.getByTestId('queue-length')).toHaveTextContent('0')

    // Set initial queue
    fireEvent.click(screen.getByText('Set Initial Queue'))

    await waitFor(() => {
      expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
    })

    // Check all tracks are in queue
    expect(screen.getByTestId('track-0')).toHaveTextContent('Test Track 1')
    expect(screen.getByTestId('track-1')).toHaveTextContent('Test Track 2')
    expect(screen.getByTestId('track-2')).toHaveTextContent('Test Track 3')

    // First track should be current
    expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')

    // Add a duplicate track
    fireEvent.click(screen.getByText('Add Track 1'))

    await waitFor(() => {
      expect(screen.getByTestId('queue-length')).toHaveTextContent('4')
    })

    // Remove track at index 1
    fireEvent.click(screen.getByText('Remove Index 1'))

    await waitFor(() => {
      expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
    })

    // Clear the queue
    fireEvent.click(screen.getByText('Clear Queue'))

    await waitFor(() => {
      expect(screen.getByTestId('queue-length')).toHaveTextContent('0')
    })
  })

  it('should handle queue reordering', async () => {
    render(
      <AudioPlayerProvider>
        <TestQueue />
      </AudioPlayerProvider>
    )

    // Set initial queue
    fireEvent.click(screen.getByText('Set Initial Queue'))

    await waitFor(() => {
      expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
    })

    // Initial order
    expect(screen.getByTestId('track-0')).toHaveTextContent('Test Track 1')
    expect(screen.getByTestId('track-1')).toHaveTextContent('Test Track 2')
    expect(screen.getByTestId('track-2')).toHaveTextContent('Test Track 3')

    // Move first track to third position
    fireEvent.click(screen.getByText('Move First to Third'))

    await waitFor(() => {
      // After moving, order should be: Track 2, Track 3, Track 1
      expect(screen.getByTestId('track-0')).toHaveTextContent('Test Track 2')
      expect(screen.getByTestId('track-1')).toHaveTextContent('Test Track 3')
      expect(screen.getByTestId('track-2')).toHaveTextContent('Test Track 1')
    })
  })
})