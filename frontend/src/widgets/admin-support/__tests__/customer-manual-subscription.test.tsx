import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ComponentProps } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { CustomerManualSubscription } from '../customer-manual-subscription';
import { STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION } from '../customer-manual-subscription-model';

const safeManualSubscriptionResult = {
  audit_action: STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION,
  config_delivery_required: true,
  created: false,
  duration_days: 30,
  expires_at: '2026-06-03T09:30:00Z',
  operation: 'extend' as const,
  previous_expires_at: '2026-05-04T09:30:00Z',
  remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
  status: 'active',
  subscription_url_changed: true,
  user_id: 'customer-1',
};

function renderPanel(
  overrides: Partial<ComponentProps<typeof CustomerManualSubscription>> = {},
) {
  const onApply = vi.fn().mockResolvedValue(safeManualSubscriptionResult);
  render(
    <CustomerManualSubscription
      actorRole="operator"
      customerLabel="alpha@example.com"
      onApply={onApply}
      userId="customer-1"
      {...overrides}
    />,
  );
  return { onApply };
}

describe('CustomerManualSubscription', () => {
  it('submits a sanitized manual grant and renders a safe success summary', async () => {
    const user = userEvent.setup();
    const { onApply } = renderPanel();

    await user.clear(screen.getByLabelText('Duration days'));
    await user.type(screen.getByLabelText('Duration days'), '30');
    await user.clear(screen.getByLabelText('Device limit'));
    await user.type(screen.getByLabelText('Device limit'), '3');
    await user.type(screen.getByLabelText('Traffic GB'), '2');
    await user.type(
      screen.getByLabelText('Operator reason'),
      'payment provider failed; manual access approved',
    );
    await user.click(screen.getByRole('button', { name: 'Apply access' }));

    await waitFor(() => {
      expect(onApply).toHaveBeenCalledWith({
        device_limit: 3,
        duration_days: 30,
        reason: 'payment provider failed; manual access approved',
        traffic_limit_bytes: 2_147_483_648,
      });
    });
    expect(await screen.findByRole('status')).toHaveTextContent(
      STAGE1_MANUAL_SUBSCRIPTION_AUDIT_ACTION,
    );

    const visibleText = document.body.textContent ?? '';
    expect(visibleText).not.toContain('subscription_url');
    expect(visibleText).not.toContain('short_uuid');
    expect(visibleText).not.toContain('https://');
  });

  it('allows unlimited traffic by sending null traffic limit', async () => {
    const user = userEvent.setup();
    const { onApply } = renderPanel();

    await user.type(screen.getByLabelText('Operator reason'), 'manual beta access approved');
    await user.click(screen.getByRole('button', { name: 'Apply access' }));

    await waitFor(() => {
      expect(onApply).toHaveBeenCalledWith({
        device_limit: 1,
        duration_days: 30,
        reason: 'manual beta access approved',
        traffic_limit_bytes: null,
      });
    });
  });

  it('blocks roles without backend permission before submit', async () => {
    const user = userEvent.setup();
    const { onApply } = renderPanel({ actorRole: 'support' });

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Manual subscription grants are restricted',
    );
    expect(screen.getByRole('button', { name: 'Apply access' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Apply access' }));

    expect(onApply).not.toHaveBeenCalled();
  });

  it('shows local validation errors without calling the backend', async () => {
    const user = userEvent.setup();
    const { onApply } = renderPanel();

    await user.clear(screen.getByLabelText('Duration days'));
    await user.type(screen.getByLabelText('Duration days'), '366');
    await user.type(screen.getByLabelText('Operator reason'), 'manual beta access approved');
    await user.click(screen.getByRole('button', { name: 'Apply access' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Manual subscription duration must be between 1 and 365 days.',
    );
    expect(onApply).not.toHaveBeenCalled();
  });

  it('does not render raw upstream errors', async () => {
    const user = userEvent.setup();
    const rawSecretError = new Error(
      'Remnawave failed: https://sub.example.local/raw-secret-token',
    );
    const onApply = vi.fn().mockRejectedValue(rawSecretError);
    renderPanel({ onApply });

    await user.type(screen.getByLabelText('Operator reason'), 'manual beta access approved');
    await user.click(screen.getByRole('button', { name: 'Apply access' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(
      'Manual subscription operation failed. Escalate to owner support review.',
    );
    expect(document.body.textContent).not.toContain('raw-secret-token');
  });
});
