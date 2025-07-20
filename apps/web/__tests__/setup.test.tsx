import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

describe('Test Setup Verification', () => {
  it('should render a simple component', () => {
    render(<div data-testid="test">Hello Test</div>)
    expect(screen.getByTestId('test')).toHaveTextContent('Hello Test')
  })

  it('should have working jest-dom matchers', () => {
    render(<button disabled>Click me</button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('should have working mocks', () => {
    const mockFn = jest.fn()
    mockFn('test')
    expect(mockFn).toHaveBeenCalledWith('test')
  })
})