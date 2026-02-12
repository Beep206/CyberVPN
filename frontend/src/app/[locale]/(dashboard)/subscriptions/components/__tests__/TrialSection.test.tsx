/**
 * TrialSection Component Tests
 *
 * Tests the three trial states:
 * 1. Eligible - Shows activation button and features
 * 2. Active - Shows trial badge with days remaining
 * 3. Hidden - Not eligible and not active
 *
 * Also tests activation flow and error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TrialSection } from '../TrialSection';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

const API_BASE = 'http://localhost:8000/api/v1';

// Wrapper for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
};

describe('TrialSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Eligible State', () => {
    it('test_shows_activation_button_when_eligible', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: true,
            is_active: false,
            trial_end: null,
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Try CyberVPN Free for 7 Days/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Start Free Trial/i)).toBeInTheDocument();
      expect(screen.getByText(/No credit card required/i)).toBeInTheDocument();
    });

    it('test_displays_trial_features_when_eligible', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: true,
            is_active: false,
            trial_end: null,
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Unlimited bandwidth/i)).toBeInTheDocument();
        expect(screen.getByText(/All server locations/i)).toBeInTheDocument();
        expect(screen.getByText(/Multi-device support/i)).toBeInTheDocument();
        expect(screen.getByText(/Premium protocols/i)).toBeInTheDocument();
      });
    });

    it('test_activates_trial_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: true,
            is_active: false,
            trial_end: null,
          });
        }),
        http.post(`${API_BASE}/trial/activate`, () => {
          return HttpResponse.json({
            message: 'Trial activated',
            trial_end: '2026-02-18T12:00:00Z',
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Start Free Trial/i)).toBeInTheDocument();
      });

      const activateButton = screen.getByText(/Start Free Trial/i);
      await user.click(activateButton);

      // Should show activating state
      await waitFor(() => {
        expect(screen.getByText(/Activating.../i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_activation_fails_400', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: true,
            is_active: false,
            trial_end: null,
          });
        }),
        http.post(`${API_BASE}/trial/activate`, () => {
          return HttpResponse.json(
            { detail: 'Not eligible for trial' },
            { status: 400 }
          );
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Start Free Trial/i)).toBeInTheDocument();
      });

      const activateButton = screen.getByText(/Start Free Trial/i);
      await user.click(activateButton);

      await waitFor(() => {
        expect(screen.getByText(/You are not eligible for a trial/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_trial_already_activated_409', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: true,
            is_active: false,
            trial_end: null,
          });
        }),
        http.post(`${API_BASE}/trial/activate`, () => {
          return HttpResponse.json(
            { detail: 'Trial already active' },
            { status: 409 }
          );
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Start Free Trial/i)).toBeInTheDocument();
      });

      const activateButton = screen.getByText(/Start Free Trial/i);
      await user.click(activateButton);

      await waitFor(() => {
        expect(screen.getByText(/Trial already activated/i)).toBeInTheDocument();
      });
    });
  });

  describe('Active Trial State', () => {
    it('test_shows_active_trial_badge_with_days_remaining', async () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 5);

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: false,
            is_active: true,
            trial_end: futureDate.toISOString(),
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Free Trial Active/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/5 days remaining/i)).toBeInTheDocument();
    });

    it('test_shows_expiring_soon_warning_when_2_days_left', async () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 2);

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: false,
            is_active: true,
            trial_end: futureDate.toISOString(),
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(
          screen.getByText(/Your trial is expiring soon. Choose a plan to continue access./i)
        ).toBeInTheDocument();
      });
    });

    it('test_shows_normal_message_when_more_than_2_days_left', async () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 5);

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: false,
            is_active: true,
            trial_end: futureDate.toISOString(),
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(
          screen.getByText(/Enjoy full access to all premium features during your trial period./i)
        ).toBeInTheDocument();
      });
    });

    it('test_displays_trial_expiry_date', async () => {
      const futureDate = new Date('2026-03-15T00:00:00Z');

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: false,
            is_active: true,
            trial_end: futureDate.toISOString(),
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Expires:/i)).toBeInTheDocument();
        expect(screen.getByText(/3\/15\/2026/i)).toBeInTheDocument();
      });
    });

    it('test_calculates_1_day_remaining_singular', async () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);

      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: false,
            is_active: true,
            trial_end: tomorrow.toISOString(),
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/1 day remaining/i)).toBeInTheDocument();
      });
    });
  });

  describe('Hidden State', () => {
    it('test_hides_section_when_not_eligible_and_not_active', async () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, () => {
          return HttpResponse.json({
            is_eligible: false,
            is_active: false,
            trial_end: null,
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByText(/Free Trial/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('test_shows_loading_skeleton_while_fetching', () => {
      server.use(
        http.get(`${API_BASE}/trial/status`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({
            is_eligible: true,
            is_active: false,
            trial_end: null,
          });
        })
      );

      render(<TrialSection />, { wrapper: createWrapper() });

      // Should show loading state initially
      const card = document.querySelector('.animate-pulse');
      expect(card).toBeInTheDocument();
    });
  });
});
