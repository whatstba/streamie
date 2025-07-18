import React from 'react'
import { render, screen, fireEvent, waitFor } from '../utils/test-utils'
import { mockTracks, createMockAudioElement, triggerAudioEvent } from '../utils/test-utils'
import Player from '@/components/player/Player'
import AudioControls from '@/components/player/AudioControls'
import { useAudioPlayer } from '@/context/AudioPlayerContext'

// Mock the audio element creation
let mockAudioElement: any

beforeEach(() => {
  mockAudioElement = createMockAudioElement()
  global.Audio = jest.fn(() => mockAudioElement) as any
})

describe('Audio Playback Integration', () => {
  describe('Basic Playback Flow', () => {
    it('should load and play a track when selected', async () => {
      // Component to test player interaction
      const TestComponent = () => {
        const { loadTrack, currentTrack, isPlaying } = useAudioPlayer()
        
        return (
          <div>
            <button onClick={() => loadTrack(mockTracks[0])}>
              Load Track 1
            </button>
            <div data-testid="current-track">
              {currentTrack?.title || 'No track'}
            </div>
            <div data-testid="is-playing">{isPlaying ? 'Playing' : 'Paused'}</div>
            <AudioControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Initially no track loaded
      expect(screen.getByTestId('current-track')).toHaveTextContent('No track')
      expect(screen.getByTestId('is-playing')).toHaveTextContent('Paused')

      // Load a track
      fireEvent.click(screen.getByText('Load Track 1'))

      // Verify track is loaded
      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Verify audio element was set up
      expect(mockAudioElement.src).toBe('/api/stream?path=%2Ftest%2Ftrack1.mp3')
      expect(mockAudioElement.load).toHaveBeenCalled()

      // Simulate successful load
      triggerAudioEvent(mockAudioElement, 'loadedmetadata', {
        target: { duration: 180 }
      })

      // Play the track
      const playButton = screen.getByRole('button', { name: /play/i })
      fireEvent.click(playButton)

      expect(mockAudioElement.play).toHaveBeenCalled()

      // Simulate play event
      mockAudioElement.paused = false
      triggerAudioEvent(mockAudioElement, 'play')

      await waitFor(() => {
        expect(screen.getByTestId('is-playing')).toHaveTextContent('Playing')
      })
    })

    it('should pause and resume playback', async () => {
      const TestComponent = () => {
        const { loadTrack, isPlaying } = useAudioPlayer()
        
        React.useEffect(() => {
          loadTrack(mockTracks[0])
        }, [loadTrack])
        
        return (
          <div>
            <div data-testid="is-playing">{isPlaying ? 'Playing' : 'Paused'}</div>
            <AudioControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for track to load
      await waitFor(() => {
        expect(mockAudioElement.load).toHaveBeenCalled()
      })

      // Simulate track loaded and play
      triggerAudioEvent(mockAudioElement, 'loadedmetadata')
      
      const playPauseButton = screen.getByRole('button', { name: /play/i })
      fireEvent.click(playPauseButton)

      mockAudioElement.paused = false
      triggerAudioEvent(mockAudioElement, 'play')

      await waitFor(() => {
        expect(screen.getByTestId('is-playing')).toHaveTextContent('Playing')
      })

      // Pause
      fireEvent.click(screen.getByRole('button', { name: /pause/i }))
      expect(mockAudioElement.pause).toHaveBeenCalled()

      mockAudioElement.paused = true
      triggerAudioEvent(mockAudioElement, 'pause')

      await waitFor(() => {
        expect(screen.getByTestId('is-playing')).toHaveTextContent('Paused')
      })
    })

    it('should handle track navigation (next/previous)', async () => {
      const TestComponent = () => {
        const { setQueue, currentTrack, currentIndex } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">
              {currentTrack?.title || 'No track'}
            </div>
            <div data-testid="queue-index">{currentIndex}</div>
            <AudioControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for first track to load
      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Go to next track
      const nextButton = screen.getByRole('button', { name: /next/i })
      fireEvent.click(nextButton)

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('1')
      })

      // Go to next track again
      fireEvent.click(nextButton)

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 3')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('2')
      })

      // Go back to previous
      const prevButton = screen.getByRole('button', { name: /previous/i })
      fireEvent.click(prevButton)

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('1')
      })
    })

    it('should update playback progress', async () => {
      const TestComponent = () => {
        const { loadTrack, currentTime, duration } = useAudioPlayer()
        
        React.useEffect(() => {
          loadTrack(mockTracks[0])
        }, [loadTrack])
        
        return (
          <div>
            <div data-testid="current-time">{currentTime}</div>
            <div data-testid="duration">{duration}</div>
            <Player />
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for track to load
      await waitFor(() => {
        expect(mockAudioElement.load).toHaveBeenCalled()
      })

      // Simulate metadata loaded
      mockAudioElement.duration = 180
      triggerAudioEvent(mockAudioElement, 'loadedmetadata')

      await waitFor(() => {
        expect(screen.getByTestId('duration')).toHaveTextContent('180')
      })

      // Simulate time update
      mockAudioElement.currentTime = 45
      triggerAudioEvent(mockAudioElement, 'timeupdate')

      await waitFor(() => {
        expect(screen.getByTestId('current-time')).toHaveTextContent('45')
      })

      // Simulate more time updates
      mockAudioElement.currentTime = 90
      triggerAudioEvent(mockAudioElement, 'timeupdate')

      await waitFor(() => {
        expect(screen.getByTestId('current-time')).toHaveTextContent('90')
      })
    })

    it('should handle volume control', async () => {
      const TestComponent = () => {
        const { loadTrack, volume, setVolume } = useAudioPlayer()
        
        React.useEffect(() => {
          loadTrack(mockTracks[0])
        }, [loadTrack])
        
        return (
          <div>
            <div data-testid="volume">{volume}</div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={volume}
              onChange={(e) => setVolume(parseFloat(e.target.value))}
              data-testid="volume-slider"
            />
          </div>
        )
      }

      render(<TestComponent />)

      // Initial volume
      expect(screen.getByTestId('volume')).toHaveTextContent('1')

      // Change volume
      const volumeSlider = screen.getByTestId('volume-slider')
      fireEvent.change(volumeSlider, { target: { value: '0.5' } })

      await waitFor(() => {
        expect(screen.getByTestId('volume')).toHaveTextContent('0.5')
        expect(mockAudioElement.volume).toBe(0.5)
      })

      // Mute
      fireEvent.change(volumeSlider, { target: { value: '0' } })

      await waitFor(() => {
        expect(screen.getByTestId('volume')).toHaveTextContent('0')
        expect(mockAudioElement.volume).toBe(0)
      })
    })

    it('should handle seek functionality', async () => {
      const TestComponent = () => {
        const { loadTrack, currentTime, duration, seek } = useAudioPlayer()
        
        React.useEffect(() => {
          loadTrack(mockTracks[0])
        }, [loadTrack])
        
        return (
          <div>
            <div data-testid="current-time">{currentTime}</div>
            <button onClick={() => seek(60)}>Seek to 60s</button>
            <button onClick={() => seek(120)}>Seek to 120s</button>
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for track to load and set duration
      mockAudioElement.duration = 180
      triggerAudioEvent(mockAudioElement, 'loadedmetadata')

      // Seek to 60 seconds
      fireEvent.click(screen.getByText('Seek to 60s'))

      await waitFor(() => {
        expect(mockAudioElement.currentTime).toBe(60)
      })

      // Simulate timeupdate after seek
      triggerAudioEvent(mockAudioElement, 'timeupdate')

      await waitFor(() => {
        expect(screen.getByTestId('current-time')).toHaveTextContent('60')
      })

      // Seek to 120 seconds
      fireEvent.click(screen.getByText('Seek to 120s'))

      await waitFor(() => {
        expect(mockAudioElement.currentTime).toBe(120)
      })
    })

    it('should handle track end and auto-advance', async () => {
      const TestComponent = () => {
        const { setQueue, currentTrack, currentIndex } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">
              {currentTrack?.title || 'No track'}
            </div>
            <div data-testid="queue-index">{currentIndex}</div>
          </div>
        )
      }

      render(<TestComponent />)

      // Wait for first track
      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Simulate track ended
      mockAudioElement.ended = true
      triggerAudioEvent(mockAudioElement, 'ended')

      // Should auto-advance to next track
      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
        expect(screen.getByTestId('queue-index')).toHaveTextContent('1')
      })
    })
  })
})