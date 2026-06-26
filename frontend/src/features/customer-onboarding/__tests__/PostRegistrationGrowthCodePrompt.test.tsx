import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PostRegistrationGrowthCodePrompt } from '../PostRegistrationGrowthCodePrompt';

const { apiMocks, routerReplaceMock } = vi.hoisted(() => ({
  apiMocks: {
    applyGrowthCode: vi.fn(),
    current: vi.fn(),
    skipGrowthCode: vi.fn(),
  },
  routerReplaceMock: vi.fn(),
}));

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api');
  return {
    ...actual,
    customerOnboardingApi: apiMocks,
  };
});

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    replace: routerReplaceMock,
  }),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const messages: Record<string, string> = {
      apply: 'Apply code',
      allowedAny: 'Any code',
      allowedLabel: 'Accepted code types',
      codeLabel: 'Growth code',
      codePlaceholder: 'Paste code',
      continue: 'Continue',
      description: 'Use one onboarding code field.',
      eyebrow: 'Onboarding',
      loading: 'Loading onboarding state...',
      maskedCodeFallback: 'code',
      redirecting: 'Opening your cabinet...',
      retry: 'Retry',
      skip: 'Skip for now',
      title: 'Apply a growth code',
      'codeTypes.gift': 'Gift',
      'codeTypes.invite': 'Invite',
      'codeTypes.promo': 'Promo',
      'messages.applyFailed': 'Apply failed',
      'messages.completed': 'Code accepted',
      'messages.flowTokenExpired': 'Flow token expired',
      'messages.promoStaged': `Promo code ${String(values?.code ?? '')} is ready`,
      'messages.skipFailed': 'Skip failed',
      'messages.skipped': 'Skipped',
      'messages.stateUnavailable': 'State unavailable',
    };
    return messages[key] ?? key;
  },
}));

function createCurrentResponse(overrides: Record<string, unknown> = {}) {
  return {
    required: true,
    status: 'pending' as const,
    flow_key: 'post_registration_growth_code_v1',
    version: 1,
    allowed_code_types: ['promo' as const, 'invite' as const, 'gift' as const],
    flow_token: 'flow-token',
    message_key: 'onboarding.required',
    server_state_available: true,
    referral_already_attributed: false,
    ...overrides,
  };
}

function renderPrompt(surface: 'web' | 'miniapp' = 'web') {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <PostRegistrationGrowthCodePrompt surface={surface} />
    </QueryClientProvider>,
  );
}

describe('PostRegistrationGrowthCodePrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.current.mockResolvedValue({ data: createCurrentResponse() });
    apiMocks.applyGrowthCode.mockResolvedValue({
      data: {
        status: 'completed',
        message_key: 'onboarding.code.promo_staged',
        masked_code: 'PRIV****',
        next_destination: '/subscriptions',
      },
    });
    apiMocks.skipGrowthCode.mockResolvedValue({
      data: {
        status: 'skipped',
        message_key: 'onboarding.skipped',
        next_destination: '/dashboard',
      },
    });
  });

  it('applies a normalized code with the server flow token and redirects to the returned destination', async () => {
    const user = userEvent.setup();

    renderPrompt();

    fireEvent.change(await screen.findByLabelText('Growth code'), {
      target: { value: ' private90 ' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply code' }));

    await waitFor(() => {
      expect(apiMocks.applyGrowthCode).toHaveBeenCalledWith({
        code: 'PRIVATE90',
        flow_token: 'flow-token',
      });
    });
    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/subscriptions');
    });
  });

  it('skips with the current flow token and maps dashboard destination for miniapp', async () => {
    const user = userEvent.setup();

    renderPrompt('miniapp');

    await user.click(await screen.findByRole('button', { name: 'Skip for now' }));

    await waitFor(() => {
      expect(apiMocks.skipGrowthCode).toHaveBeenCalledWith({
        flow_token: 'flow-token',
      });
    });
    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('does not show the prompt when backend state is already completed', async () => {
    apiMocks.current.mockResolvedValue({
      data: createCurrentResponse({ required: false, status: 'completed' }),
    });

    renderPrompt();

    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/dashboard');
    });
  });
});
