import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { listUnresolvedDropReceipts, reconcileDropReceipt } = vi.hoisted(() => ({
  listUnresolvedDropReceipts: vi.fn(),
  reconcileDropReceipt: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/lib/api/remnawave-connections', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-connections')>();
  return {
    ...actual,
    adminRemnawaveConnectionsApi: {
      ...actual.adminRemnawaveConnectionsApi,
      listUnresolvedDropReceipts,
      reconcileDropReceipt,
    },
  };
});

import { RemnawaveConnectionReconciliationQueue } from './remnawave-connection-reconciliation-queue';

const RECEIPT_ID = 'b'.repeat(43);
const UNRESOLVED_RECEIPT = {
  receipt_id: RECEIPT_ID,
  state: 'outcome_unknown' as const,
  audience: 'admin' as const,
  created_at: '2026-08-31T10:00:00Z',
  updated_at: '2026-08-31T10:01:00Z',
  expires_at: null,
  expires_in_seconds: null,
  requires_reconciliation: true,
  reconciled_at: null,
  reconciliation_reason: null,
  reconciliation_reference: null,
};

function renderQueue() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RemnawaveConnectionReconciliationQueue />
    </QueryClientProvider>,
  );
}

async function openReconciliationForm(user: ReturnType<typeof userEvent.setup>) {
  const table = await screen.findByRole('table', { name: 'reconciliation.table.caption' });
  await user.click(within(table).getByRole('button', { name: 'reconciliation.actions.select' }));
}

async function submitReference(user: ReturnType<typeof userEvent.setup>, reference = 'case-abc123') {
  await user.type(screen.getByLabelText('reconciliation.form.reference'), reference);
  await user.click(screen.getByRole('checkbox', { name: 'reconciliation.form.confirm' }));
  await user.click(screen.getByRole('button', { name: 'reconciliation.actions.reconcile' }));
}

describe('RemnawaveConnectionReconciliationQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listUnresolvedDropReceipts.mockResolvedValue({
      items: [UNRESOLVED_RECEIPT],
      next_cursor: null,
    });
    reconcileDropReceipt.mockResolvedValue({
      ...UNRESOLVED_RECEIPT,
      state: 'accepted',
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 7_200,
      requires_reconciliation: false,
      updated_at: '2026-08-31T10:05:00Z',
      reconciled_at: '2026-08-31T10:05:00Z',
      reconciliation_reason: 'provider_confirmed_applied',
      reconciliation_reference: 'CASE-ABC123',
    });
  });

  it('announces the bounded queue loading state', () => {
    listUnresolvedDropReceipts.mockReturnValue(new Promise(() => undefined));

    renderQueue();

    expect(screen.getByText('reconciliation.states.loading')).toHaveAttribute('role', 'status');
    expect(listUnresolvedDropReceipts).toHaveBeenCalledWith({ limit: 25, cursor: null });
  });

  it('renders an explicit empty state', async () => {
    listUnresolvedDropReceipts.mockResolvedValue({ items: [], next_cursor: null });

    renderQueue();

    expect(await screen.findByText('reconciliation.states.empty')).toHaveAttribute('role', 'status');
  });

  it('keeps a 503 list failure degraded until a manual refresh succeeds', async () => {
    listUnresolvedDropReceipts
      .mockRejectedValueOnce({ response: { status: 503 } })
      .mockResolvedValueOnce({ items: [], next_cursor: null });
    const user = userEvent.setup();
    renderQueue();

    expect(await screen.findByRole('alert')).toHaveTextContent('reconciliation.errors.unavailable');
    await user.click(screen.getAllByRole('button', { name: 'reconciliation.actions.refresh' })[1]);

    expect(await screen.findByText('reconciliation.states.empty')).toBeInTheDocument();
    expect(listUnresolvedDropReceipts).toHaveBeenCalledTimes(2);
  });

  it('records an accepted result with compatible public fields only', async () => {
    const user = userEvent.setup();
    renderQueue();
    await openReconciliationForm(user);

    expect(screen.queryByLabelText(/ttl|hmac|scope|raw payload/i)).not.toBeInTheDocument();
    await submitReference(user);

    expect(await screen.findByText('reconciliation.states.success.accepted')).toHaveAttribute('role', 'status');
    expect(reconcileDropReceipt).toHaveBeenCalledTimes(1);
    expect(reconcileDropReceipt).toHaveBeenCalledWith(RECEIPT_ID, {
      outcome: 'accepted',
      reason: 'provider_confirmed_applied',
      reference: 'CASE-ABC123',
    });
    expect(Object.keys(reconcileDropReceipt.mock.calls[0][1]).sort()).toEqual([
      'outcome',
      'reason',
      'reference',
    ]);
  });

  it('offers only not-applied reasons for a rejected result', async () => {
    reconcileDropReceipt.mockResolvedValue({
      ...UNRESOLVED_RECEIPT,
      state: 'rejected',
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 7_200,
      requires_reconciliation: false,
      reconciled_at: '2026-08-31T10:05:00Z',
      reconciliation_reason: 'provider_confirmed_not_applied',
      reconciliation_reference: 'TKT-XYZ789',
    });
    const user = userEvent.setup();
    renderQueue();
    await openReconciliationForm(user);

    await user.selectOptions(screen.getByLabelText('reconciliation.form.outcome'), 'rejected');
    const reasonSelect = screen.getByLabelText('reconciliation.form.reason');
    expect(within(reasonSelect).queryByRole('option', {
      name: 'reconciliation.reasons.provider_confirmed_applied',
    })).not.toBeInTheDocument();
    expect(within(reasonSelect).getByRole('option', {
      name: 'reconciliation.reasons.provider_confirmed_not_applied',
    })).toBeInTheDocument();
    await submitReference(user, 'tkt-xyz789');

    expect(await screen.findByText('reconciliation.states.success.rejected')).toBeInTheDocument();
    expect(reconcileDropReceipt).toHaveBeenCalledWith(RECEIPT_ID, {
      outcome: 'rejected',
      reason: 'provider_confirmed_not_applied',
      reference: 'TKT-XYZ789',
    });
  });

  it('associates validation with a malformed bounded reference and does not mutate', async () => {
    const user = userEvent.setup();
    renderQueue();
    await openReconciliationForm(user);

    await user.type(screen.getByLabelText('reconciliation.form.reference'), 'free form');
    await user.click(screen.getByRole('button', { name: 'reconciliation.actions.reconcile' }));

    expect(screen.getByRole('alert')).toHaveTextContent('reconciliation.form.validation');
    expect(screen.getByLabelText('reconciliation.form.reference')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('reconciliation.form.reference')).toHaveAttribute('maxLength', '64');
    expect(reconcileDropReceipt).not.toHaveBeenCalled();
  });

  it.each([
    [404, 'reconciliation.errors.notFound'],
    [409, 'reconciliation.errors.conflict'],
    [503, 'reconciliation.errors.unavailable'],
  ])('renders the explicit %s mutation error without assuming success', async (status, key) => {
    reconcileDropReceipt.mockRejectedValue({ response: { status } });
    const user = userEvent.setup();
    renderQueue();
    await openReconciliationForm(user);
    await submitReference(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(key);
    expect(screen.queryByText('reconciliation.states.success.accepted')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'reconciliation.actions.reconcile' })).toBeDisabled();
    await user.click(screen.getByRole('checkbox', { name: 'reconciliation.form.confirm' }));
    await user.click(screen.getByRole('checkbox', { name: 'reconciliation.form.confirm' }));
    expect(screen.getByRole('button', { name: 'reconciliation.actions.reconcile' })).toBeDisabled();
    expect(reconcileDropReceipt).toHaveBeenCalledTimes(1);
  });

  it('uses opaque cursors for bounded next and previous navigation', async () => {
    const nextCursor = 'c'.repeat(43);
    listUnresolvedDropReceipts
      .mockResolvedValueOnce({ items: [UNRESOLVED_RECEIPT], next_cursor: nextCursor })
      .mockResolvedValueOnce({ items: [], next_cursor: null })
      .mockResolvedValueOnce({ items: [UNRESOLVED_RECEIPT], next_cursor: nextCursor });
    const user = userEvent.setup();
    renderQueue();

    await screen.findByRole('table', { name: 'reconciliation.table.caption' });
    await user.click(screen.getByRole('button', { name: 'reconciliation.actions.next' }));
    expect(await screen.findByText('reconciliation.states.empty')).toBeInTheDocument();
    expect(listUnresolvedDropReceipts).toHaveBeenLastCalledWith({
      limit: 25,
      cursor: nextCursor,
    });

    await user.click(screen.getByRole('button', { name: 'reconciliation.actions.previous' }));
    await screen.findByRole('table', { name: 'reconciliation.table.caption' });
    expect(listUnresolvedDropReceipts).toHaveBeenLastCalledWith({ limit: 25, cursor: null });
  });
});
