// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Mock HTMLMediaElement for audio testing
window.HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve())
window.HTMLMediaElement.prototype.pause = jest.fn()
window.HTMLMediaElement.prototype.load = jest.fn()

// Mock Web Audio API
const mockAudioContext = {
  createGain: jest.fn(() => ({
    gain: { value: 1, setValueAtTime: jest.fn(), linearRampToValueAtTime: jest.fn() },
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createMediaElementSource: jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createBiquadFilter: jest.fn(() => ({
    type: '',
    frequency: { value: 0 },
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createDelay: jest.fn(() => ({
    delayTime: { value: 0 },
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createAnalyser: jest.fn(() => ({
    fftSize: 2048,
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createConvolver: jest.fn(() => ({
    buffer: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createWaveShaper: jest.fn(() => ({
    curve: null,
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  destination: {},
  currentTime: 0,
  state: 'running',
  resume: jest.fn().mockResolvedValue(undefined),
}

global.AudioContext = jest.fn(() => mockAudioContext)
global.webkitAudioContext = jest.fn(() => mockAudioContext)

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}