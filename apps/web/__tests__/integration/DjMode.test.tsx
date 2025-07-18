import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '../utils/test-utils'
import { mockTracks, createMockAudioElement, triggerAudioEvent } from '../utils/test-utils'
import { createMockAudioContext, createMockGainNode, verifyCrossfadeRamp } from '../utils/mockAudioContext'
import DjModeControls from '@/components/player/DjModeControls'
import { useAudioPlayer } from '@/context/AudioPlayerContext'

let mockAudioElement: any
let mockNextAudioElement: any
let mockAudioContext: any

beforeEach(() => {
  mockAudioElement = createMockAudioElement()
  mockNextAudioElement = createMockAudioElement()
  mockAudioContext = createMockAudioContext()
  
  let audioCount = 0
  global.Audio = jest.fn(() => {
    return audioCount++ === 0 ? mockAudioElement : mockNextAudioElement
  }) as any
  
  global.AudioContext = jest.fn(() => mockAudioContext) as any
  
  jest.useFakeTimers()
})

afterEach(() => {
  jest.useRealTimers()
})

describe('DJ Mode Integration', () => {
  describe('DJ Mode Transitions', () => {
    it('should enable DJ mode and configure transition settings', async () => {
      const TestComponent = () => {
        const { djMode, setQueue } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="dj-enabled">{djMode.enabled ? 'Yes' : 'No'}</div>
            <div data-testid="mix-mode">{djMode.mixMode}</div>
            <div data-testid="mix-interval">{djMode.mixInterval}</div>
            <div data-testid="crossfade-duration">{djMode.crossfadeDuration}</div>
            <DjModeControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Initially disabled
      expect(screen.getByTestId('dj-enabled')).toHaveTextContent('No')

      // Enable DJ mode
      const djToggle = screen.getByRole('switch', { name: /dj mode/i })
      fireEvent.click(djToggle)

      await waitFor(() => {
        expect(screen.getByTestId('dj-enabled')).toHaveTextContent('Yes')
      })

      // Check default settings
      expect(screen.getByTestId('mix-mode')).toHaveTextContent('interval')
      expect(screen.getByTestId('mix-interval')).toHaveTextContent('30')
      expect(screen.getByTestId('crossfade-duration')).toHaveTextContent('5')

      // Change mix mode
      const modeSelect = screen.getByLabelText(/mix mode/i)
      fireEvent.change(modeSelect, { target: { value: 'track-end' } })

      await waitFor(() => {
        expect(screen.getByTestId('mix-mode')).toHaveTextContent('track-end')
      })

      // Change crossfade duration
      const crossfadeSlider = screen.getByLabelText(/crossfade duration/i)
      fireEvent.change(crossfadeSlider, { target: { value: '10' } })

      await waitFor(() => {
        expect(screen.getByTestId('crossfade-duration')).toHaveTextContent('10')
      })
    })

    it('should handle automatic crossfade in interval mode', async () => {
      const TestComponent = () => {
        const { djMode, setQueue, currentTrack, isTransitioning, loadTrack } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <button onClick={() => loadTrack(mockTracks[0])}>Start Playing</button>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="is-transitioning">{isTransitioning ? 'Yes' : 'No'}</div>
            <div data-testid="dj-enabled">{djMode.enabled ? 'Yes' : 'No'}</div>
            <DjModeControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Enable DJ mode with short interval for testing
      const djToggle = screen.getByRole('switch', { name: /dj mode/i })
      fireEvent.click(djToggle)

      // Set mix interval to 5 seconds
      const intervalSlider = screen.getByLabelText(/mix interval/i)
      fireEvent.change(intervalSlider, { target: { value: '5' } })

      // Start playing
      fireEvent.click(screen.getByText('Start Playing'))

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Simulate track playing
      mockAudioElement.paused = false
      triggerAudioEvent(mockAudioElement, 'play')

      // Fast forward 5 seconds (mix interval)
      act(() => {
        mockAudioElement.currentTime = 5
        triggerAudioEvent(mockAudioElement, 'timeupdate')
        jest.advanceTimersByTime(5000)
      })

      // Should start transitioning
      await waitFor(() => {
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('Yes')
      })

      // Verify next track is being prepared
      expect(mockNextAudioElement.src).toContain('track2.mp3')
      expect(mockNextAudioElement.load).toHaveBeenCalled()

      // Verify Web Audio API setup for crossfade
      expect(mockAudioContext.createGain).toHaveBeenCalledTimes(2) // Current and next gain nodes
      expect(mockAudioContext.createMediaElementSource).toHaveBeenCalledTimes(2)
    })

    it('should handle manual mix trigger', async () => {
      const TestComponent = () => {
        const { djMode, setQueue, currentTrack, isTransitioning, transitionProgress, mixNow } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="is-transitioning">{isTransitioning ? 'Yes' : 'No'}</div>
            <div data-testid="transition-progress">{transitionProgress}</div>
            <button onClick={mixNow} disabled={!djMode.enabled || isTransitioning}>
              Mix Now
            </button>
            <DjModeControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Enable DJ mode
      const djToggle = screen.getByRole('switch', { name: /dj mode/i })
      fireEvent.click(djToggle)

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Start playing
      mockAudioElement.paused = false
      triggerAudioEvent(mockAudioElement, 'play')

      // Trigger manual mix
      const mixNowButton = screen.getByText('Mix Now')
      fireEvent.click(mixNowButton)

      await waitFor(() => {
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('Yes')
      })

      // Simulate transition progress
      act(() => {
        jest.advanceTimersByTime(2500) // Half of 5s crossfade
      })

      await waitFor(() => {
        const progress = parseInt(screen.getByTestId('transition-progress').textContent || '0')
        expect(progress).toBeGreaterThan(40)
        expect(progress).toBeLessThan(60)
      })

      // Complete transition
      act(() => {
        jest.advanceTimersByTime(2500) // Complete the 5s crossfade
      })

      await waitFor(() => {
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('No')
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
      })
    })

    it('should handle track-end mix mode', async () => {
      const TestComponent = () => {
        const { djMode, setQueue, currentTrack, isTransitioning } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="is-transitioning">{isTransitioning ? 'Yes' : 'No'}</div>
            <DjModeControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Enable DJ mode with track-end mode
      const djToggle = screen.getByRole('switch', { name: /dj mode/i })
      fireEvent.click(djToggle)

      const modeSelect = screen.getByLabelText(/mix mode/i)
      fireEvent.change(modeSelect, { target: { value: 'track-end' } })

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Simulate track playing
      mockAudioElement.paused = false
      mockAudioElement.duration = 180
      triggerAudioEvent(mockAudioElement, 'play')
      triggerAudioEvent(mockAudioElement, 'loadedmetadata')

      // Fast forward to near end of track (5s before end with 5s crossfade)
      act(() => {
        mockAudioElement.currentTime = 175
        triggerAudioEvent(mockAudioElement, 'timeupdate')
      })

      // Should start transitioning
      await waitFor(() => {
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('Yes')
      })

      // Simulate track ending
      act(() => {
        mockAudioElement.currentTime = 180
        mockAudioElement.ended = true
        triggerAudioEvent(mockAudioElement, 'ended')
        jest.advanceTimersByTime(5000)
      })

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('No')
      })
    })

    it('should handle volume-based crossfade fallback', async () => {
      // Simulate Web Audio API not available
      global.AudioContext = undefined as any
      global.webkitAudioContext = undefined as any

      const TestComponent = () => {
        const { djMode, setQueue, currentTrack, isTransitioning, mixNow } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="is-transitioning">{isTransitioning ? 'Yes' : 'No'}</div>
            <button onClick={mixNow}>Mix Now</button>
            <DjModeControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Enable DJ mode
      const djToggle = screen.getByRole('switch', { name: /dj mode/i })
      fireEvent.click(djToggle)

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 1')
      })

      // Start playing
      mockAudioElement.paused = false
      triggerAudioEvent(mockAudioElement, 'play')

      // Trigger manual mix
      fireEvent.click(screen.getByText('Mix Now'))

      await waitFor(() => {
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('Yes')
      })

      // Verify volume-based crossfade is being used
      expect(mockAudioElement.volume).toBeLessThan(1)
      expect(mockNextAudioElement.volume).toBeGreaterThan(0)

      // Simulate crossfade progress
      act(() => {
        jest.advanceTimersByTime(2500) // Half of 5s crossfade
      })

      // Volumes should be approximately equal at midpoint
      expect(mockAudioElement.volume).toBeCloseTo(0.5, 1)
      expect(mockNextAudioElement.volume).toBeCloseTo(0.5, 1)

      // Complete transition
      act(() => {
        jest.advanceTimersByTime(2500)
      })

      await waitFor(() => {
        expect(screen.getByTestId('is-transitioning')).toHaveTextContent('No')
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
      })

      // Final volumes
      expect(mockAudioElement.volume).toBe(0)
      expect(mockNextAudioElement.volume).toBe(1)
    })

    it('should maintain DJ settings between tracks', async () => {
      const TestComponent = () => {
        const { djMode, setQueue, currentTrack } = useAudioPlayer()
        
        React.useEffect(() => {
          setQueue(mockTracks)
        }, [setQueue])
        
        return (
          <div>
            <div data-testid="current-track">{currentTrack?.title || 'None'}</div>
            <div data-testid="mix-interval">{djMode.mixInterval}</div>
            <div data-testid="crossfade-duration">{djMode.crossfadeDuration}</div>
            <DjModeControls />
          </div>
        )
      }

      render(<TestComponent />)

      // Configure DJ settings
      const djToggle = screen.getByRole('switch', { name: /dj mode/i })
      fireEvent.click(djToggle)

      const intervalSlider = screen.getByLabelText(/mix interval/i)
      fireEvent.change(intervalSlider, { target: { value: '45' } })

      const crossfadeSlider = screen.getByLabelText(/crossfade duration/i)
      fireEvent.change(crossfadeSlider, { target: { value: '8' } })

      await waitFor(() => {
        expect(screen.getByTestId('mix-interval')).toHaveTextContent('45')
        expect(screen.getByTestId('crossfade-duration')).toHaveTextContent('8')
      })

      // Simulate track change
      mockAudioElement.ended = true
      triggerAudioEvent(mockAudioElement, 'ended')

      await waitFor(() => {
        expect(screen.getByTestId('current-track')).toHaveTextContent('Test Track 2')
      })

      // Settings should be maintained
      expect(screen.getByTestId('mix-interval')).toHaveTextContent('45')
      expect(screen.getByTestId('crossfade-duration')).toHaveTextContent('8')
    })
  })
})