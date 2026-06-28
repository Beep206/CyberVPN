import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PostRegistrationGrowthCodePrompt } from '../PostRegistrationGrowthCodePrompt';

const { apiMocks, routerReplaceMock } = vi.hoisted(() => ({
  apiMocks: {
    applyGrowthCode: vi.fn(),
    connectionBootstrap: vi.fn(),
    current: vi.fn(),
    markConnected: vi.fn(),
    previewGrowthCode: vi.fn(),
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

vi.mock('../ConnectionBootstrapPanel', () => ({
  ConnectionBootstrapPanel: ({ surface }: { surface: string }) => (
    <div data-testid="connection-panel">connection panel {surface}</div>
  ),
}));

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
      'messages.giftRedeemed': `Gift code ${String(values?.code ?? '')} redeemed`,
      'messages.inviteRedeemed': `Invite code ${String(values?.code ?? '')} redeemed`,
      'messages.promoStaged': `Promo code ${String(values?.code ?? '')} is ready`,
      'messages.skipFailed': 'Skip failed',
      'messages.skipped': 'Skipped',
      'messages.stateUnavailable': 'State unavailable',
      'preview.ambiguous': 'Code matches several namespaces',
      'preview.available': 'This code can be applied',
      'preview.gift': 'Gift code is valid',
      'preview.invite': 'Invite code is valid',
      'preview.loading': 'Checking code...',
      'preview.maskedCode': `Checked: ${String(values?.code ?? '')}`,
      'preview.networkError': 'Preview unavailable',
      'preview.promoCheckout': 'Promo code is valid for checkout',
      'preview.retry': 'Retry preview',
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
    apiMocks.previewGrowthCode.mockResolvedValue({
      data: {
        accepted: true,
        detected_code_type: 'promo',
        status: 'wrong_context',
        message_key: 'growth_codes.promo.checkout_required',
        masked_code: 'PRIV****',
        matched_code_types: ['promo'],
        next_action: 'stage_for_checkout',
        safe_details: {},
      },
    });
    apiMocks.applyGrowthCode.mockResolvedValue({
      data: {
        status: 'completed',
        message_key: 'onboarding.code.promo_staged',
        masked_code: 'PRIV****',
        next_destination: '/subscriptions',
        connection_required: false,
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

  afterEach(() => {
    vi.useRealTimers();
  });

  it('applies a normalized code with the server flow token, idempotency key, and returned destination', async () => {
    const user = userEvent.setup();

    renderPrompt();

    fireEvent.change(await screen.findByLabelText('Growth code'), {
      target: { value: ' private90 ' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply code' }));

    await waitFor(() => {
      expect(apiMocks.applyGrowthCode).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'PRIVATE90',
          flow_token: 'flow-token',
          idempotency_key: expect.stringMatching(/^onboarding-apply:/),
          source_surface: 'web',
        }),
      );
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
      expect(apiMocks.skipGrowthCode).toHaveBeenCalledWith(
        expect.objectContaining({
          flow_token: 'flow-token',
          idempotency_key: expect.stringMatching(/^onboarding-skip:/),
        }),
      );
    });
    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('does not show the prompt when backend state is already completed', async () => {
    apiMocks.current.mockResolvedValue({
      data: createCurrentResponse({ required: false, status: 'completed', connection_required: false }),
    });

    renderPrompt();

    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('shows connection bootstrap from completed shared state without reapplying the code', async () => {
    apiMocks.current.mockResolvedValue({
      data: createCurrentResponse({
        required: false,
        status: 'completed',
        flow_token: null,
        connection_required: true,
      }),
    });

    renderPrompt('miniapp');

    expect(await screen.findByTestId('connection-panel')).toHaveTextContent('connection panel miniapp');
    expect(apiMocks.applyGrowthCode).not.toHaveBeenCalled();
    expect(routerReplaceMock).not.toHaveBeenCalledWith('/miniapp/home');
  });

  it('shows connection bootstrap after an entitlement code completes instead of redirecting', async () => {
    const user = userEvent.setup();
    apiMocks.current
      .mockResolvedValueOnce({ data: createCurrentResponse() })
      .mockResolvedValueOnce({
        data: createCurrentResponse({
          required: false,
          status: 'completed',
          flow_token: null,
        }),
      });
    apiMocks.applyGrowthCode.mockResolvedValue({
      data: {
        status: 'completed',
        message_key: 'growth_codes.invite.accepted',
        masked_code: 'INV****',
        next_destination: '/dashboard',
        connection_required: true,
      },
    });

    renderPrompt('miniapp');

    fireEvent.change(await screen.findByLabelText('Growth code'), {
      target: { value: ' invite7 ' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply code' }));

    expect(await screen.findByTestId('connection-panel')).toHaveTextContent('connection panel miniapp');
    await waitFor(() => {
      expect(apiMocks.current).toHaveBeenCalledTimes(2);
    });
    expect(screen.getByTestId('connection-panel')).toHaveTextContent('connection panel miniapp');
    await waitFor(() => {
      expect(apiMocks.applyGrowthCode).toHaveBeenCalledWith(
        expect.objectContaining({
          source_surface: 'miniapp',
        }),
      );
    });
    expect(routerReplaceMock).not.toHaveBeenCalledWith('/miniapp/home');
  });

  it('does not infer connection bootstrap from invite copy without the typed signal', async () => {
    const user = userEvent.setup();
    apiMocks.applyGrowthCode.mockResolvedValue({
      data: {
        status: 'completed',
        message_key: 'growth_codes.invite.accepted',
        masked_code: 'INV****',
        next_destination: '/dashboard',
        connection_required: false,
      },
    });

    renderPrompt('miniapp');

    fireEvent.change(await screen.findByLabelText('Growth code'), {
      target: { value: ' invite7 ' },
    });
    await user.click(screen.getByRole('button', { name: 'Apply code' }));

    expect(screen.queryByTestId('connection-panel')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(routerReplaceMock).toHaveBeenCalledWith('/miniapp/home');
    });
  });

  it('debounces preview requests with the current flow token and only sends the latest normalized code', async () => {
    renderPrompt();

    const input = await screen.findByLabelText('Growth code');
    fireEvent.change(input, { target: { value: ' gift9 ' } });
    expect(apiMocks.previewGrowthCode).not.toHaveBeenCalled();

    await waitFor(() => {
      expect(apiMocks.previewGrowthCode).toHaveBeenCalledTimes(1);
    });
    expect(apiMocks.previewGrowthCode).toHaveBeenCalledWith({
      code: 'GIFT9',
      flow_token: 'flow-token',
    });
  });

  it('blocks apply when preview reports an ambiguous namespace', async () => {
    const user = userEvent.setup();
    apiMocks.previewGrowthCode.mockResolvedValue({
      data: {
        accepted: false,
        detected_code_type: null,
        status: 'ambiguous',
        message_key: 'growth_codes.code_namespace_ambiguous',
        masked_code: 'AMB****',
        matched_code_types: ['invite', 'promo'],
        next_action: 'resolve_ambiguity',
        safe_details: { reject_reason: 'code_namespace_ambiguous' },
      },
    });

    renderPrompt();

    fireEvent.change(await screen.findByLabelText('Growth code'), {
      target: { value: ' ambig ' },
    });

    expect(await screen.findByText('Code matches several namespaces')).toBeInTheDocument();
    const applyButton = screen.getByRole('button', { name: 'Apply code' });
    expect(applyButton).toBeDisabled();
    await user.click(applyButton);

    expect(apiMocks.applyGrowthCode).not.toHaveBeenCalled();
  });

  it('reuses apply idempotency for the same normalized code and resets it after the code changes', async () => {
    apiMocks.applyGrowthCode.mockRejectedValue(new Error('network failed'));

    renderPrompt();

    const input = await screen.findByLabelText('Growth code');

    fireEvent.change(input, { target: { value: ' invite7 ' } });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Apply code' })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply code' }));
    await waitFor(() => {
      expect(apiMocks.applyGrowthCode).toHaveBeenCalledTimes(1);
    });
    const firstKey = apiMocks.applyGrowthCode.mock.calls[0][0].idempotency_key;

    fireEvent.click(screen.getByRole('button', { name: 'Apply code' }));
    await waitFor(() => {
      expect(apiMocks.applyGrowthCode).toHaveBeenCalledTimes(2);
    });
    expect(apiMocks.applyGrowthCode.mock.calls[1][0].idempotency_key).toBe(firstKey);

    const updatedInput = screen.getByLabelText('Growth code');
    fireEvent.change(updatedInput, { target: { value: 'gift9' } });
    await waitFor(() => {
      expect(updatedInput).toHaveValue('gift9');
    });
    await waitFor(() => {
      expect(apiMocks.previewGrowthCode).toHaveBeenLastCalledWith({
        code: 'GIFT9',
        flow_token: 'flow-token',
      });
    });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Apply code' })).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply code' }));
    await waitFor(() => {
      expect(apiMocks.applyGrowthCode).toHaveBeenCalledTimes(3);
    });
    expect(apiMocks.applyGrowthCode.mock.calls[2][0]).toEqual(
      expect.objectContaining({
        code: 'GIFT9',
        idempotency_key: expect.stringMatching(/^onboarding-apply:/),
      }),
    );
    expect(apiMocks.applyGrowthCode.mock.calls[2][0].idempotency_key).not.toBe(firstKey);
  });
});
