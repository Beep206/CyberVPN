/**
 * PartnerClient Component Tests
 *
 * Tests both views of the Partner Dashboard:
 * 1. Non-Partner View - Bind form for becoming a partner
 * 2. Partner View - Dashboard, code creation, earnings display
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PartnerClient } from '../PartnerClient';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock CyberInput
vi.mock('@/features/auth/components/CyberInput', () => ({
  CyberInput: ({ label, value, onChange, error, placeholder, onKeyDown, disabled }: any) => (
    <div>
      <label>{label}</label>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        onKeyDown={onKeyDown}
        aria-label={label}
      />
      {error && <span role="alert">{error}</span>}
    </div>
  ),
}));

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: any) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
};

describe('PartnerClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('Non-Partner View (403 - Not a Partner)', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/partner/dashboard`, () => {
          return HttpResponse.json(
            { detail: 'Not a partner' },
            { status: 403 }
          );
        })
      );
    });

    it('test_shows_become_partner_form_when_not_partner', async () => {
      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Become a Partner/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Enter your partner code to access the partner dashboard/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      expect(screen.getByText(/Bind Partner Code/i)).toBeInTheDocument();
    });

    it('test_converts_partner_code_to_uppercase', async () => {
      const user = userEvent.setup({ delay: null });

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Partner Code/i) as HTMLInputElement;
      await user.type(input, 'partner');

      expect(input.value).toBe('PARTNER');
    });

    it('test_binds_to_partner_successfully', async () => {
      const user = userEvent.setup({ delay: null });
      const reloadMock = vi.fn();
      Object.defineProperty(window, 'location', {
        value: { reload: reloadMock },
        writable: true,
      });

      server.use(
        http.post(`${API_BASE}/partner/bind`, () => {
          return HttpResponse.json({
            message: 'Successfully bound to partner',
          });
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Partner Code/i);
      await user.type(input, 'PARTNER2024');

      const bindButton = screen.getByText(/Bind Partner Code/i);
      await user.click(bindButton);

      await waitFor(() => {
        expect(screen.getByText(/Successfully bound to partner!/i)).toBeInTheDocument();
      });

      // Advance timer for reload
      vi.advanceTimersByTime(2000);

      await waitFor(() => {
        expect(reloadMock).toHaveBeenCalled();
      });
    });

    it('test_shows_error_for_invalid_partner_code', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/partner/bind`, () => {
          return HttpResponse.json(
            { detail: 'Invalid partner code' },
            { status: 404 }
          );
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Partner Code/i);
      await user.type(input, 'INVALID');

      const bindButton = screen.getByText(/Bind Partner Code/i);
      await user.click(bindButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid partner code/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_binding_empty_code', async () => {
      const user = userEvent.setup({ delay: null });

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Bind Partner Code/i)).toBeInTheDocument();
      });

      const bindButton = screen.getByText(/Bind Partner Code/i);
      await user.click(bindButton);

      await waitFor(() => {
        expect(screen.getByText(/Please enter a partner code/i)).toBeInTheDocument();
      });
    });

    it('test_disables_button_while_binding', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/partner/bind`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ message: 'Success' });
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Partner Code/i);
      await user.type(input, 'CODE123');

      const bindButton = screen.getByText(/Bind Partner Code/i);
      await user.click(bindButton);

      await waitFor(() => {
        expect(screen.getByText(/Binding.../i)).toBeInTheDocument();
      });
    });
  });

  describe('Partner View (Successful Dashboard Load)', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/partner/dashboard`, () => {
          return HttpResponse.json({
            total_earnings: 250.50,
            active_codes_count: 5,
            referrals_count: 12,
          });
        }),
        http.get(`${API_BASE}/partner/codes`, () => {
          return HttpResponse.json([
            { code: 'SUMMER2024', markup_percent: 15, uses_count: 8, earnings: 120.00 },
            { code: 'WELCOME10', markup_percent: 10, uses_count: 4, earnings: 40.50 },
          ]);
        }),
        http.get(`${API_BASE}/partner/earnings`, () => {
          return HttpResponse.json([
            { created_at: '2026-02-10T12:00:00Z', code: 'SUMMER2024', amount: 25.00 },
            { created_at: '2026-02-09T12:00:00Z', code: 'WELCOME10', amount: 15.50 },
          ]);
        })
      );
    });

    it('test_displays_dashboard_stats', async () => {
      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Total Earnings/i)).toBeInTheDocument();
      });

      expect(screen.getByText('$250.5')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // Active codes
      expect(screen.getByText('12')).toBeInTheDocument(); // Referrals
    });

    it('test_displays_partner_codes_table', async () => {
      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('SUMMER2024')).toBeInTheDocument();
      });

      expect(screen.getByText('WELCOME10')).toBeInTheDocument();
      expect(screen.getByText('15%')).toBeInTheDocument();
      expect(screen.getByText('10%')).toBeInTheDocument();
      expect(screen.getByText('$120')).toBeInTheDocument();
      expect(screen.getByText('$40.5')).toBeInTheDocument();
    });

    it('test_displays_recent_earnings_table', async () => {
      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Recent Earnings/i)).toBeInTheDocument();
      });

      expect(screen.getAllByText(/SUMMER2024/i)).toHaveLength(2); // In codes table and earnings table
      expect(screen.getByText('$25')).toBeInTheDocument();
      expect(screen.getByText('$15.5')).toBeInTheDocument();
    });

    it('test_creates_new_partner_code_successfully', async () => {
      const user = userEvent.setup({ delay: null });

      server.use(
        http.post(`${API_BASE}/partner/codes`, () => {
          return HttpResponse.json({
            code: 'NEWCODE2024',
            markup_percent: 20,
          }, { status: 201 });
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Code Name/i)).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(/Code Name/i);
      const markupInput = screen.getByLabelText(/Markup %/i);
      const createButton = screen.getByText('Create');

      await user.type(nameInput, 'newcode2024');
      await user.type(markupInput, '20');
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getByText(/Creating.../i)).toBeInTheDocument();
      });
    });

    it('test_validates_code_name_required', async () => {
      const user = userEvent.setup({ delay: null });

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Create')).toBeInTheDocument();
      });

      const markupInput = screen.getByLabelText(/Markup %/i);
      const createButton = screen.getByText('Create');

      await user.type(markupInput, '15');
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getByText(/Code name is required/i)).toBeInTheDocument();
      });
    });

    it('test_validates_markup_range_0_to_100', async () => {
      const user = userEvent.setup({ delay: null });

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Code Name/i)).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(/Code Name/i);
      const markupInput = screen.getByLabelText(/Markup %/i);
      const createButton = screen.getByText('Create');

      // Test > 100
      await user.type(nameInput, 'TEST');
      await user.type(markupInput, '150');
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getByText(/Markup must be between 0-100/i)).toBeInTheDocument();
      });
    });

    it('test_converts_code_name_to_uppercase', async () => {
      const user = userEvent.setup({ delay: null });

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Code Name/i)).toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(/Code Name/i) as HTMLInputElement;
      await user.type(nameInput, 'lowercase');

      expect(nameInput.value).toBe('LOWERCASE');
    });

    it('test_shows_empty_state_when_no_codes', async () => {
      server.use(
        http.get(`${API_BASE}/partner/codes`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/No partner codes yet/i)).toBeInTheDocument();
      });
    });

    it('test_hides_earnings_section_when_no_earnings', async () => {
      server.use(
        http.get(`${API_BASE}/partner/earnings`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Total Earnings/i)).toBeInTheDocument();
      });

      expect(screen.queryByText(/Recent Earnings/i)).not.toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('test_shows_dashboard_loading_skeleton', () => {
      server.use(
        http.get(`${API_BASE}/partner/dashboard`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({});
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      const skeletons = document.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });
});
