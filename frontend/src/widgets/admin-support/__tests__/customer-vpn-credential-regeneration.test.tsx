import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ComponentProps } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { CustomerVpnCredentialRegeneration } from '../customer-vpn-credential-regeneration';
import { STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION } from '../customer-vpn-credential-regeneration-model';

const safeCredentialRegenerationResult = {
  audit_action: STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION,
  config_delivery_required: true,
  expires_at: '2026-06-03T09:30:00Z',
  regenerated_at: '2026-05-04T09:30:00Z',
  remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
  revoke_only_passwords: false,
  short_uuid_changed: true,
  status: 'ACTIVE',
  subscription_url_changed: true,
  user_id: 'customer-1',
};

function renderPanel(
  overrides: Partial<ComponentProps<typeof CustomerVpnCredentialRegeneration>> = {},
) {
  const onRegenerate = vi.fn().mockResolvedValue(safeCredentialRegenerationResult);
  render(
    <CustomerVpnCredentialRegeneration
      actorRole="support"
      customerLabel="alpha@example.com"
      onRegenerate={onRegenerate}
      userId="customer-1"
      {...overrides}
    />,
  );
  return { onRegenerate };
}

describe('CustomerVpnCredentialRegeneration', () => {
  it('submits a sanitized request and renders a safe success summary', async () => {
    const user = userEvent.setup();
    const { onRegenerate } = renderPanel();

    await user.type(
      screen.getByLabelText('Support reason'),
      'customer lost device; rotate VPN credentials',
    );
    await user.click(screen.getByRole('button', { name: 'Regenerate credentials' }));

    await waitFor(() => {
      expect(onRegenerate).toHaveBeenCalledWith({
        reason: 'customer lost device; rotate VPN credentials',
        revoke_only_passwords: false,
      });
    });
    expect(await screen.findByRole('status')).toHaveTextContent(
      STAGE1_CREDENTIAL_REGENERATION_AUDIT_ACTION,
    );

    const visibleText = document.body.textContent ?? '';
    expect(visibleText).not.toContain('subscription_url');
    expect(visibleText).not.toContain('short_uuid');
    expect(visibleText).not.toContain('https://');
  });

  it('supports the Remnawave password-only rotation mode', async () => {
    const user = userEvent.setup();
    const { onRegenerate } = renderPanel();

    await user.type(screen.getByLabelText('Support reason'), 'rotate protocol passwords only');
    await user.click(
      screen.getByRole('checkbox', {
        name: /revoke only protocol passwords/i,
      }),
    );
    await user.click(screen.getByRole('button', { name: 'Regenerate credentials' }));

    await waitFor(() => {
      expect(onRegenerate).toHaveBeenCalledWith({
        reason: 'rotate protocol passwords only',
        revoke_only_passwords: true,
      });
    });
  });

  it('blocks roles without backend permission before submit', async () => {
    const user = userEvent.setup();
    const { onRegenerate } = renderPanel({ actorRole: 'operator' });

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Credential rotation is restricted',
    );
    expect(screen.getByRole('button', { name: 'Regenerate credentials' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Regenerate credentials' }));

    expect(onRegenerate).not.toHaveBeenCalled();
  });

  it('shows local validation errors without calling the backend', async () => {
    const user = userEvent.setup();
    const { onRegenerate } = renderPanel();

    await user.type(screen.getByLabelText('Support reason'), 'no');
    await user.click(screen.getByRole('button', { name: 'Regenerate credentials' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Credential regeneration requires a support reason.',
    );
    expect(onRegenerate).not.toHaveBeenCalled();
  });

  it('does not render raw provider errors', async () => {
    const user = userEvent.setup();
    const rawSecretError = new Error(
      'Remnawave failed: https://sub.example.local/raw-secret-token',
    );
    const onRegenerate = vi.fn().mockRejectedValue(rawSecretError);
    renderPanel({ onRegenerate });

    await user.type(screen.getByLabelText('Support reason'), 'customer reported compromise');
    await user.click(screen.getByRole('button', { name: 'Regenerate credentials' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(
      'Credential regeneration failed. Escalate to manual support review.',
    );
    expect(document.body.textContent).not.toContain('raw-secret-token');
  });
});
