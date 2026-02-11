/**
 * CodesSection Component Tests
 *
 * Tests invite and promo code functionality:
 * - Invite code redemption (success, errors)
 * - Promo code validation (success, discount display, errors)
 * - My invite codes list
 * - Copy to clipboard functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CodesSection } from '../CodesSection';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock CyberInput component
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

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve()),
  },
});

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('CodesSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: no invite codes
    server.use(
      http.get(`${API_BASE}/invites/my`, () => {
        return HttpResponse.json([]);
      })
    );
  });

  describe('Invite Code Redemption', () => {
    it('test_renders_invite_code_input_and_button', async () => {
      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Invite Code/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Redeem Code/i)).toBeInTheDocument();
    });

    it('test_redeems_invite_code_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, () => {
          return HttpResponse.json({
            message: 'Invite code redeemed successfully!',
            reward: '7 days free',
          });
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Invite Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Invite Code/i);
      await user.type(input, 'CYBER2024');

      const redeemButton = screen.getByText(/Redeem Code/i);
      await user.click(redeemButton);

      await waitFor(() => {
        expect(screen.getByText(/Redeeming.../i)).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/Invite code redeemed successfully!/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_for_invalid_invite_code_404', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, () => {
          return HttpResponse.json(
            { detail: 'Code not found' },
            { status: 404 }
          );
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Invite Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Invite Code/i);
      await user.type(input, 'INVALID');

      const redeemButton = screen.getByText(/Redeem Code/i);
      await user.click(redeemButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid or expired invite code/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_for_already_redeemed_code_400', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/invites/redeem`, () => {
          return HttpResponse.json(
            { detail: 'Code already used' },
            { status: 400 }
          );
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Invite Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Invite Code/i);
      await user.type(input, 'USED123');

      const redeemButton = screen.getByText(/Redeem Code/i);
      await user.click(redeemButton);

      await waitFor(() => {
        expect(screen.getByText(/Code already used/i)).toBeInTheDocument();
      });
    });

    it('test_converts_invite_code_to_uppercase', async () => {
      const user = userEvent.setup();

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Invite Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Invite Code/i) as HTMLInputElement;
      await user.type(input, 'lowercase');

      expect(input.value).toBe('LOWERCASE');
    });

    it('test_shows_error_when_redeeming_empty_code', async () => {
      const user = userEvent.setup();

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Redeem Code/i)).toBeInTheDocument();
      });

      const redeemButton = screen.getByText(/Redeem Code/i);
      await user.click(redeemButton);

      await waitFor(() => {
        expect(screen.getByText(/Please enter an invite code/i)).toBeInTheDocument();
      });
    });
  });

  describe('Promo Code Validation', () => {
    it('test_renders_promo_code_input_and_button', async () => {
      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Promo Code/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Validate Promo/i)).toBeInTheDocument();
    });

    it('test_validates_promo_code_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/promo/validate`, () => {
          return HttpResponse.json({
            discount_percent: 20,
            expires_at: '2026-12-31T23:59:59Z',
            valid: true,
          });
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Promo Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Promo Code/i);
      await user.type(input, 'SAVE20');

      const validateButton = screen.getByText(/Validate Promo/i);
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/Valid Promo Code/i)).toBeInTheDocument();
        expect(screen.getByText(/20%/i)).toBeInTheDocument();
      });
    });

    it('test_displays_discount_amount_for_promo_code', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/promo/validate`, () => {
          return HttpResponse.json({
            discount_amount: 5.99,
            expires_at: '2026-12-31T23:59:59Z',
            valid: true,
          });
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Promo Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Promo Code/i);
      await user.type(input, 'FLAT5');

      const validateButton = screen.getByText(/Validate Promo/i);
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/\$5\.99/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_for_invalid_promo_code_404', async () => {
      const user = userEvent.setup();

      server.use(
        http.post(`${API_BASE}/promo/validate`, () => {
          return HttpResponse.json(
            { detail: 'Code not found' },
            { status: 404 }
          );
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Promo Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Promo Code/i);
      await user.type(input, 'BADCODE');

      const validateButton = screen.getByText(/Validate Promo/i);
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid or expired promo code/i)).toBeInTheDocument();
      });
    });

    it('test_converts_promo_code_to_uppercase', async () => {
      const user = userEvent.setup();

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Promo Code/i)).toBeInTheDocument();
      });

      const input = screen.getByLabelText(/Promo Code/i) as HTMLInputElement;
      await user.type(input, 'save20');

      expect(input.value).toBe('SAVE20');
    });

    it('test_shows_error_when_validating_empty_promo_code', async () => {
      const user = userEvent.setup();

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Validate Promo/i)).toBeInTheDocument();
      });

      const validateButton = screen.getByText(/Validate Promo/i);
      await user.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/Please enter a promo code/i)).toBeInTheDocument();
      });
    });
  });

  describe('My Invite Codes List', () => {
    it('test_displays_users_invite_codes', async () => {
      server.use(
        http.get(`${API_BASE}/invites/my`, () => {
          return HttpResponse.json([
            { code: 'FRIEND2024', expires_at: '2026-12-31T23:59:59Z' },
            { code: 'WELCOME123', expires_at: null },
          ]);
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/My Invite Codes/i)).toBeInTheDocument();
      });

      expect(screen.getByText('FRIEND2024')).toBeInTheDocument();
      expect(screen.getByText('WELCOME123')).toBeInTheDocument();
      expect(screen.getByText(/Expires: 12\/31\/2026/i)).toBeInTheDocument();
    });

    it('test_hides_invite_codes_section_when_empty', async () => {
      server.use(
        http.get(`${API_BASE}/invites/my`, () => {
          return HttpResponse.json([]);
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/Invite Code/i)).toBeInTheDocument();
      });

      expect(screen.queryByText(/My Invite Codes/i)).not.toBeInTheDocument();
    });

    it('test_copies_code_to_clipboard', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/invites/my`, () => {
          return HttpResponse.json([
            { code: 'COPY123', expires_at: null },
          ]);
        })
      );

      render(<CodesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('COPY123')).toBeInTheDocument();
      });

      const copyButton = screen.getByLabelText(/Copy code/i);
      await user.click(copyButton);

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('COPY123');
    });
  });
});
