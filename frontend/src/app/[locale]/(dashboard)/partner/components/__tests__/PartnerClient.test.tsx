/**
 * PartnerClient Component Tests
 *
 * Tests both views of the Partner Dashboard:
 * 1. Non-Partner View - Bind form for becoming a partner
 * 2. Partner View - Dashboard, code creation, earnings display
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PartnerClient } from '../PartnerClient';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/shared/lib/stage3-partner-flags', () => ({
  STAGE3_PARTNER_PORTAL_UI_ENABLED: true,
  STAGE3_PARTNER_PORTAL_DISABLED_REASON: 'disabled',
}));

// Mock CyberInput
vi.mock('@/features/auth/components/CyberInput', () => ({
  CyberInput: ({ label, value, onChange, error, placeholder, onKeyDown, disabled }: { label?: string; value?: string; onChange?: React.ChangeEventHandler<HTMLInputElement>; error?: string; placeholder?: string; onKeyDown?: React.KeyboardEventHandler; disabled?: boolean }) => (
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

const API_BASE = '*/api/v1';

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

describe('PartnerClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
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
      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Partner Code/i) as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'partner' } });

      await waitFor(() => {
        expect((screen.getByLabelText(/Partner Code/i) as HTMLInputElement).value).toBe('PARTNER');
      });
    });

    it('test_binds_to_partner_successfully', async () => {
      const user = userEvent.setup({ delay: null });
      let bindPayload: unknown;

      server.use(
        http.post(`${API_BASE}/partner/bind`, async ({ request }) => {
          bindPayload = await request.json();
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
      fireEvent.change(input, { target: { value: 'partner2024' } });

      const bindButton = screen.getByText(/Bind Partner Code/i);
      await user.click(bindButton);

      await waitFor(() => {
        expect(screen.getByText(/Successfully bound to partner!/i)).toBeInTheDocument();
      });

      expect(bindPayload).toEqual({ partner_code: 'PARTNER2024' });
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
      fireEvent.change(input, { target: { value: 'invalid' } });

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
      let bindRequests = 0;

      server.use(
        http.post(`${API_BASE}/partner/bind`, async () => {
          bindRequests += 1;
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ message: 'Success' });
        })
      );

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Partner Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Partner Code/i);
      fireEvent.change(input, { target: { value: 'code123' } });

      const bindButton = screen.getByText(/Bind Partner Code/i);
      await user.click(bindButton);

      await waitFor(() => {
        expect(bindRequests).toBe(1);
        expect(screen.getByText(/Binding.../i)).toBeInTheDocument();
      });
    });
  });

  describe('Partner View (Successful Dashboard Load)', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/partner/dashboard`, () => {
          return HttpResponse.json({
            total_earned: 250.50,
            total_clients: 12,
            codes: [{ id: 'code-1' }, { id: 'code-2' }, { id: 'code-3' }, { id: 'code-4' }, { id: 'code-5' }],
          });
        }),
        http.get(`${API_BASE}/partner/codes`, () => {
          return HttpResponse.json([
            {
              id: 'code-1',
              code: 'SUMMER2024',
              markup_pct: 15,
              is_active: true,
              created_at: '2026-02-01T00:00:00Z',
            },
            {
              id: 'code-2',
              code: 'WELCOME10',
              markup_pct: 10,
              is_active: true,
              created_at: '2026-02-02T00:00:00Z',
            },
          ]);
        }),
        http.get(`${API_BASE}/partner/earnings`, () => {
          return HttpResponse.json([
            {
              id: 'earning-1',
              client_user_id: 'client-user-1',
              base_price: 100,
              markup_amount: 10,
              commission_amount: 15,
              total_earning: 25,
              created_at: '2026-02-10T12:00:00Z',
            },
            {
              id: 'earning-2',
              client_user_id: 'client-user-2',
              base_price: 70,
              markup_amount: 5,
              commission_amount: 10.5,
              total_earning: 15.5,
              created_at: '2026-02-09T12:00:00Z',
            },
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
        expect(screen.getAllByText('SUMMER2024').length).toBeGreaterThan(0);
      });

      expect(screen.getAllByText('WELCOME10').length).toBeGreaterThan(0);
      expect(screen.getAllByText('15%').length).toBeGreaterThan(0);
      expect(screen.getAllByText('10%').length).toBeGreaterThan(0);
      expect(screen.getAllByText('-').length).toBeGreaterThan(0);
    });

    it('test_displays_recent_earnings_table', async () => {
      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Recent Earnings/i)).toBeInTheDocument();
      });

      expect(screen.getAllByText('$25.00').length).toBeGreaterThan(0);
      expect(screen.getAllByText('$15.50').length).toBeGreaterThan(0);
    });

    it('test_creates_new_partner_code_successfully', async () => {
      const user = userEvent.setup({ delay: null });
      let createPayload: unknown;
      let createRequests = 0;

      server.use(
        http.post(`${API_BASE}/partner/codes`, async ({ request }) => {
          createRequests += 1;
          createPayload = await request.json();
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({
            code: 'NEWCODE2024',
            markup_pct: 20,
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

      fireEvent.change(nameInput, { target: { value: 'newcode2024' } });
      fireEvent.change(markupInput, { target: { value: '20' } });
      await user.click(createButton);

      await waitFor(() => {
        expect(createRequests).toBe(1);
        expect(screen.getByText(/Creating.../i)).toBeInTheDocument();
      });

      expect(createPayload).toEqual({ code: 'NEWCODE2024', markup_pct: 20 });
    });

    it('test_validates_code_name_required', async () => {
      const user = userEvent.setup({ delay: null });

      render(<PartnerClient />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Create')).toBeInTheDocument();
      });

      const markupInput = screen.getByLabelText(/Markup %/i);
      const createButton = screen.getByText('Create');

      fireEvent.change(markupInput, { target: { value: '15' } });
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
