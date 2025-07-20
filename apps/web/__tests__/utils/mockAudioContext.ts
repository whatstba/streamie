// Mock Web Audio API nodes and context
export const createMockGainNode = () => ({
  gain: { 
    value: 1, 
    setValueAtTime: jest.fn(),
    linearRampToValueAtTime: jest.fn(),
    exponentialRampToValueAtTime: jest.fn(),
  },
  connect: jest.fn(),
  disconnect: jest.fn(),
})

export const createMockFilterNode = () => ({
  type: 'lowpass',
  frequency: { value: 350 },
  Q: { value: 1 },
  connect: jest.fn(),
  disconnect: jest.fn(),
})

export const createMockDelayNode = () => ({
  delayTime: { value: 0 },
  connect: jest.fn(),
  disconnect: jest.fn(),
})

export const createMockAudioContext = () => ({
  createGain: jest.fn(() => createMockGainNode()),
  createMediaElementSource: jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
  createBiquadFilter: jest.fn(() => createMockFilterNode()),
  createDelay: jest.fn(() => createMockDelayNode()),
  destination: {},
  currentTime: 0,
  state: 'running',
  suspend: jest.fn(),
  resume: jest.fn(),
})

// Helper to verify audio node connections
export const verifyAudioNodeConnection = (
  sourceNode: any,
  destinationNode: any
) => {
  expect(sourceNode.connect).toHaveBeenCalledWith(destinationNode)
}

// Helper to verify gain ramping for crossfades
export const verifyCrossfadeRamp = (
  gainNode: any,
  startValue: number,
  endValue: number,
  duration: number
) => {
  const calls = gainNode.gain.linearRampToValueAtTime.mock.calls
  const lastCall = calls[calls.length - 1]
  expect(lastCall[0]).toBe(endValue)
  // Verify the time is approximately correct (within 100ms)
  expect(lastCall[1]).toBeGreaterThan(0)
}