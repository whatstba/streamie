import React from 'react'
import { Track } from '@/types/music'

// Create a mock implementation of the AudioPlayerContext
export const createMockAudioPlayerContext = (overrides = {}) => {
  const defaultState = {
    // State
    currentTrack: null,
    isPlaying: false,
    isLoading: false,
    duration: 0,
    currentTime: 0,
    volume: 1,
    queue: [],
    queueIndex: 0,
    currentIndex: -1,
    shuffle: false,
    shuffleMode: false,
    repeat: 'none',
    repeatMode: 'off',
    djMode: false,
    autoTransition: false,
    transitionTime: 30,
    crossfadeDuration: 5,
    isTransitioning: false,
    transitionProgress: 0,
    nextTrack: null,
    timeUntilTransition: 0,
    bpmSyncEnabled: false,
    pitchShift: 0,
    hotCues: {},
    currentEffects: [],
    beatAlignment: true,
    loopActive: false,
    sourceBpm: null,
    targetBpm: null,
    syncRatio: 1.0,
    mixInterval: 30,
    mixMode: 'interval',
    
    // DJ Mode state
    djMode: {
      enabled: false,
      mixMode: 'interval',
      mixInterval: 30,
      crossfadeDuration: 5,
    },
    
    // Actions
    playTrack: jest.fn(),
    loadTrack: jest.fn(),
    play: jest.fn(),
    pause: jest.fn(),
    skipToNext: jest.fn(),
    skipToPrevious: jest.fn(),
    seek: jest.fn(),
    setVolume: jest.fn(),
    toggleShuffle: jest.fn(),
    toggleRepeat: jest.fn(),
    cycleRepeatMode: jest.fn(),
    addToQueue: jest.fn(),
    removeFromQueue: jest.fn((id) => {}),
    clearQueue: jest.fn(),
    moveQueueItem: jest.fn(),
    reorderQueue: jest.fn(),
    toggleDjMode: jest.fn(),
    setAutoTransition: jest.fn(),
    setTransitionTime: jest.fn(),
    setCrossfadeDuration: jest.fn(),
    forceTransition: jest.fn(),
    setQueue: jest.fn(),
    playTrackAtIndex: jest.fn(),
    mixNow: jest.fn(),
    ...overrides
  }
  
  return defaultState
}

export const MockAudioPlayerProvider = ({ children, value = {} }: { 
  children: React.ReactNode, 
  value?: any 
}) => {
  const React = require('react')
  const { AudioPlayerContext } = require('@/context/AudioPlayerContext')
  const mockValue = createMockAudioPlayerContext(value)
  
  return React.createElement(
    AudioPlayerContext.Provider,
    { value: mockValue },
    children
  )
}