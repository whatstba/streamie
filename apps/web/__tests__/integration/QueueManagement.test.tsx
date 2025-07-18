import React from 'react'
import { render, screen, fireEvent, waitFor, within } from '../utils/test-utils'
import { mockTracks, createMockAudioElement } from '../utils/test-utils'
import QueueManager from '@/components/player/QueueManager'
import { useAudioPlayer } from '@/context/AudioPlayerContext'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'

// Mock react-dnd for testing
jest.mock('react-dnd', () => ({
  useDrag: jest.fn(() => [{}, jest.fn(), jest.fn()]),
  useDrop: jest.fn(() => [{}, jest.fn()]),
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

jest.mock('react-dnd-html5-backend', () => ({
  HTML5Backend: jest.fn(),
}))

let mockAudioElement: any

beforeEach(() => {
  mockAudioElement = createMockAudioElement()
  global.Audio = jest.fn(() => mockAudioElement) as any
})

describe('Queue Management Integration', () => {
  describe('Queue Operations', () => {
    it('should display queue and current track indicator', async () => {
      const TestComponent = () => {
        const { setQueue, queue, queueIndex } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="queue-length">{queue.length}</div>
            <div data-testid="queue-index">{queueIndex}</div>
            <QueueManager />
          </div>
        )
      }

      render(<TestComponent />)

      // Verify queue is loaded
      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
      })

      // Check all tracks are displayed
      expect(screen.getByText('Test Track 1')).toBeInTheDocument()
      expect(screen.getByText('Test Track 2')).toBeInTheDocument()
      expect(screen.getByText('Test Track 3')).toBeInTheDocument()

      // First track should be marked as current
      const queueItems = screen.getAllByRole('listitem')
      expect(queueItems[0]).toHaveClass('border-blue-500')
    })

    it('should add tracks to queue', async () => {
      const TestComponent = () => {
        const { queue, addToQueue } = useAudioPlayer()
        
        const newTrack = {
          id: '4',
          title: 'New Track',
          artist: 'New Artist',
          album: 'New Album',
          duration: 210,
          file_path: '/test/new.mp3',
          album_art_url: '/test/new.jpg',
          bpm: 125,
          key: 'G',
          energy: 0.75,
          danceability: 0.85,
          valence: 0.65,
          vocal_presence: true,
          hot_cues: []
        }
        
        return (
          <div>
            <div data-testid="queue-length">{queue.length}</div>
            <button onClick={() => addToQueue(newTrack)}>Add New Track</button>
            <QueueManager />
          </div>
        )
      }

      render(<TestComponent />)

      // Initially empty queue
      expect(screen.getByTestId('queue-length')).toHaveTextContent('0')

      // Add a track
      fireEvent.click(screen.getByText('Add New Track'))

      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('1')
        expect(screen.getByText('New Track')).toBeInTheDocument()
      })
    })

    it('should remove tracks from queue', async () => {
      const TestComponent = () => {
        const { setQueue, queue, removeFromQueue } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="queue-length">{queue.length}</div>
            <div data-testid="queue-tracks">
              {queue.map(track => (
                <div key={track.id}>
                  {track.title}
                  <button onClick={() => removeFromQueue(track.id)}>
                    Remove {track.title}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for queue to load
      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
      })

      // Remove the second track
      fireEvent.click(screen.getByText('Remove Test Track 2'))

      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('2')
        expect(screen.queryByText('Test Track 2')).not.toBeInTheDocument()
      })

      // Verify remaining tracks
      expect(screen.getByText('Test Track 1')).toBeInTheDocument()
      expect(screen.getByText('Test Track 3')).toBeInTheDocument()
    })

    it('should play specific track from queue', async () => {
      const TestComponent = () => {
        const { setQueue, currentTrack, queueIndex, playTrackAtIndex } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="queue-index">{queueIndex}</div>
            <div>
              {mockTracks.map((track, index) => (
                <button key={track.id} onClick={() => playTrackAtIndex(index)}>
                  Play {track.title}
                </button>
              ))}
            </div>
          </div>
        )
      }

      render(<TestComponent />)

      // Initially playing first track
      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
      })

      // Play third track
      fireEvent.click(screen.getByText('Play Test Track 3'))

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 3')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('2')
      })

      // Play second track
      fireEvent.click(screen.getByText('Play Test Track 2'))

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('1')
      })
    })

    it('should reorder queue via drag and drop simulation', async () => {
      const TestComponent = () => {
        const { setQueue, queue, reorderQueue } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="queue-order">
              {queue.map(track => track.title).join(', ')}
            </div>
            <button 
              onClick={() => {
                // Simulate moving track 3 to position 1
                const newQueue = [...queue]
                const [removed] = newQueue.splice(2, 1)
                newQueue.splice(0, 0, removed)
                reorderQueue(newQueue)
              }}
            >
              Move Track 3 to Top
            </button>
            <button 
              onClick={() => {
                // Simulate moving track 1 to position 2
                const newQueue = [...queue]
                const [removed] = newQueue.splice(0, 1)
                newQueue.splice(1, 0, removed)
                reorderQueue(newQueue)
              }}
            >
              Move Track 1 to Middle
            </button>
          </div>
        )
      }

      render(<TestComponent />)

      // Initial order
      await waitFor(() => {
        expect(screen.getByTestId('queue-order')).toHaveTextContent(
          'Test Track 1, Test Track 2, Test Track 3'
        )
      })

      // Move track 3 to top
      fireEvent.click(screen.getByText('Move Track 3 to Top'))

      await waitFor(() => {
        expect(screen.getByTestId('queue-order')).toHaveTextContent(
          'Test Track 3, Test Track 1, Test Track 2'
        )
      })

      // Move track 1 to middle
      fireEvent.click(screen.getByText('Move Track 1 to Middle'))

      await waitFor(() => {
        expect(screen.getByTestId('queue-order')).toHaveTextContent(
          'Test Track 3, Test Track 1, Test Track 2'
        )
      })
    })

    it('should clear queue', async () => {
      const TestComponent = () => {
        const { setQueue, queue, clearQueue } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="queue-length">{queue.length}</div>
            <button onClick={clearQueue}>Clear Queue</button>
            <div data-testid="queue-tracks">
              {queue.map(track => (
                <div key={track.id}>{track.title}</div>
              ))}
            </div>
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for queue to load
      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
      })

      // Clear the queue
      fireEvent.click(screen.getByText('Clear Queue'))

      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('0')
        expect(screen.getByTestId('queue-tracks')).toBeEmptyDOMElement()
      })
    })

    it('should handle queue persistence through track changes', async () => {
      const TestComponent = () => {
        const { setQueue, queue, currentTrack, queueIndex, skipToNext } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="queue-index">{queueIndex}</div>
            <div data-testid="queue-length">{queue.length}</div>
            <button onClick={skipToNext}>Next Track</button>
          </div>
        )
      }

      render(<TestComponent />)

      // Initial state
      await waitFor(() => {
        expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('0')
      })

      // Skip to next track
      fireEvent.click(screen.getByText('Next Track'))

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('1')
        // Queue length should remain the same
        expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
      })

      // Skip again
      fireEvent.click(screen.getByText('Next Track'))

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 3')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('2')
        expect(screen.getByTestId('queue-length')).toHaveTextContent('3')
      })
    })

    it('should handle shuffle mode', async () => {
      const TestComponent = () => {
        const { setQueue, shuffleMode, toggleShuffle, queue } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="shuffle-mode">{shuffleMode ? 'On' : 'Off'}</div>
            <div data-testid="queue-order">
              {queue.map(track => track.title).join(', ')}
            </div>
            <button onClick={toggleShuffle}>Toggle Shuffle</button>
          </div>
        )
      }

      // Mock Math.random for predictable shuffle
      const originalRandom = Math.random
      Math.random = jest.fn(() => 0.5)

      render(<TestComponent />)

      // Initially shuffle is off
      await waitFor(() => {
        expect(screen.getByTestId('shuffle-mode')).toHaveTextContent('Off')
      })

      // Toggle shuffle on
      fireEvent.click(screen.getByText('Toggle Shuffle'))

      await waitFor(() => {
        expect(screen.getByTestId('shuffle-mode')).toHaveTextContent('On')
      })

      // Queue order might change when shuffle is enabled
      // The actual order depends on the shuffle algorithm

      // Toggle shuffle off
      fireEvent.click(screen.getByText('Toggle Shuffle'))

      await waitFor(() => {
        expect(screen.getByTestId('shuffle-mode')).toHaveTextContent('Off')
      })

      // Restore original Math.random
      Math.random = originalRandom
    })

    it('should handle repeat modes', async () => {
      const TestComponent = () => {
        const { setQueue, repeatMode, cycleRepeatMode, currentTrack } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="repeat-mode">{repeatMode}</div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <button onClick={cycleRepeatMode}>Cycle Repeat</button>
          </div>
        )
      }

      render(<TestComponent />)

      // Initially repeat is off
      await waitFor(() => {
        expect(screen.getByTestId('repeat-mode')).toHaveTextContent('off')
      })

      // Cycle to repeat all
      fireEvent.click(screen.getByText('Cycle Repeat'))

      await waitFor(() => {
        expect(screen.getByTestId('repeat-mode')).toHaveTextContent('all')
      })

      // Cycle to repeat one
      fireEvent.click(screen.getByText('Cycle Repeat'))

      await waitFor(() => {
        expect(screen.getByTestId('repeat-mode')).toHaveTextContent('one')
      })

      // Cycle back to off
      fireEvent.click(screen.getByText('Cycle Repeat'))

      await waitFor(() => {
        expect(screen.getByTestId('repeat-mode')).toHaveTextContent('off')
      })
    })
  })
})