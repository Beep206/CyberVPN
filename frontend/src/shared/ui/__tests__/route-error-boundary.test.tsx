/**
 * RouteErrorBoundary Component Tests
 *
 * Tests the error boundary component used in error.tsx files:
 * - Renders error message when error prop provided
 * - "Try Again" button calls reset function
 * - Sentry.captureException is called with the error
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouteErrorBoundary } from '../route-error-boundary';

// Mock @sentry/nextjs
const mockCaptureException = vi.fn();
vi.mock('@sentry/nextjs', () => ({
  captureException: mockCaptureException,
}));

// Mock next/link
vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe('RouteErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders error message when error prop is provided', () => {
    const testError = new Error('Test error message');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    // Should display the error message
    expect(screen.getByText(/Test error message/i)).toBeInTheDocument();
  });

  it('renders error digest when provided', () => {
    const testError = Object.assign(new Error('Test error'), {
      digest: 'abc123',
    });
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    expect(screen.getByText(/abc123/i)).toBeInTheDocument();
  });

  it('renders "UNKNOWN" when no digest is provided', () => {
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    expect(screen.getByText(/UNKNOWN/i)).toBeInTheDocument();
  });

  it('calls reset function when "Try Again" button is clicked', async () => {
    const user = userEvent.setup();
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    const tryAgainButton = screen.getByText(/Try Again/i);
    await user.click(tryAgainButton);

    expect(mockReset).toHaveBeenCalledTimes(1);
  });

  it('calls Sentry.captureException with the error on mount', () => {
    const testError = new Error('Test error for Sentry');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    expect(mockCaptureException).toHaveBeenCalledWith(testError);
    expect(mockCaptureException).toHaveBeenCalledTimes(1);
  });

  it('calls Sentry.captureException again when error changes', () => {
    const testError1 = new Error('First error');
    const testError2 = new Error('Second error');
    const mockReset = vi.fn();

    const { rerender } = render(
      <RouteErrorBoundary error={testError1} reset={mockReset} />
    );

    expect(mockCaptureException).toHaveBeenCalledWith(testError1);

    // Change error prop
    rerender(<RouteErrorBoundary error={testError2} reset={mockReset} />);

    expect(mockCaptureException).toHaveBeenCalledWith(testError2);
    expect(mockCaptureException).toHaveBeenCalledTimes(2);
  });

  it('renders "Go Home" link to /dashboard', () => {
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    const goHomeLink = screen.getByText(/Go Home/i);
    expect(goHomeLink).toBeInTheDocument();
    expect(goHomeLink).toHaveAttribute('href', '/dashboard');
  });

  it('renders cyberpunk-themed UI elements', () => {
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    // Check for error header
    expect(screen.getByText(/ERROR/i)).toBeInTheDocument();
    expect(screen.getByText(/SYSTEM MALFUNCTION DETECTED/i)).toBeInTheDocument();

    // Check for monitoring message
    expect(screen.getByText(/REPORT LOGGED TO MONITORING SYSTEM/i)).toBeInTheDocument();
  });
});
