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
const { mockCaptureException } = vi.hoisted(() => ({
  mockCaptureException: vi.fn(),
}));
vi.mock('@sentry/nextjs', () => ({
  addBreadcrumb: vi.fn(),
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

    // Should display the error message in the visible log and stack details.
    expect(screen.getAllByText(/Test error message/i).length).toBeGreaterThan(0);
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

  it('calls reset function when the reboot button is clicked', async () => {
    const user = userEvent.setup();
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    const tryAgainButton = screen.getByText(/Reboot System/i);
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

  it('renders dashboard return link', () => {
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    const goHomeLink = screen.getByText(/Return to Base/i);
    expect(goHomeLink).toBeInTheDocument();
    expect(goHomeLink).toHaveAttribute('href', '/dashboard');
  });

  it('renders cyberpunk-themed UI elements', () => {
    const testError = new Error('Test error');
    const mockReset = vi.fn();

    render(<RouteErrorBoundary error={testError} reset={mockReset} />);

    expect(screen.getByText(/SYSTEM FAILURE/i)).toBeInTheDocument();
    expect(screen.getByText(/Critical Error Detected/i)).toBeInTheDocument();
    expect(screen.getByText(/ERROR_LOG/i)).toBeInTheDocument();
  });
});
