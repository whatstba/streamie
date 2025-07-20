import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { AudioPlayerProvider } from '@/context/AudioPlayerContext'
import { Track } from '@/types/music'

// Mock track data for tests
export const mockTracks: Track[] = [
  {
    filename: 'track1.mp3',
    filepath: '/test/track1.mp3',
    title: 'Test Track 1',
    artist: 'Test Artist 1',
    album: 'Test Album 1',
    duration: 180,
    genre: 'Electronic',
    year: '2024',
    has_artwork: true,
    bpm: 120,
  },
  {
    filename: 'track2.mp3',
    filepath: '/test/track2.mp3',
    title: 'Test Track 2',
    artist: 'Test Artist 2',
    album: 'Test Album 2',
    duration: 240,
    genre: 'House',
    year: '2024',
    has_artwork: true,
    bpm: 128,
  },
  {
    filename: 'track3.mp3',
    filepath: '/test/track3.mp3',
    title: 'Test Track 3',
    artist: 'Test Artist 3',
    album: 'Test Album 3',
    duration: 200,
    genre: 'Techno',
    year: '2024',
    has_artwork: true,
    bpm: 140,
  }
]

// Custom render function that includes providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return <AudioPlayerProvider>{children}</AudioPlayerProvider>
}

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

// Mock audio element factory
export const createMockAudioElement = () => {
  const audioElement = {
    play: jest.fn().mockResolvedValue(undefined),
    pause: jest.fn(),
    load: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    currentTime: 0,
    duration: 180,
    volume: 1,
    paused: true,
    ended: false,
    src: '',
    playbackRate: 1,
    dispatchEvent: jest.fn(),
  }

  // Allow tests to trigger events
  audioElement.addEventListener.mockImplementation((event, handler) => {
    audioElement[`_${event}Handler`] = handler
  })

  return audioElement as any
}

// Helper to trigger audio events
export const triggerAudioEvent = (audioElement: any, event: string, data?: any) => {
  const handler = audioElement[`_${event}Handler`]
  if (handler) {
    handler({ ...data, type: event, target: audioElement })
  }
}

// Helper to wait for state updates
export const waitForStateUpdate = () => 
  new Promise(resolve => setTimeout(resolve, 0))

// Re-export everything
export * from '@testing-library/react'
export { customRender as render }