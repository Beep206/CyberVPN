import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import {
  PrivateOfferUnlock,
  type PrivateOfferUnlockCopy,
} from '../PrivateOfferUnlock';
import { server } from '@/test/mocks/server';

const API_V3_PREFLIGHT = '*/api/v3/growth/code-sets/preflight';
const PRIVATE_GRANT_ID = '99999999-9999-4999-8999-999999999999';

const copy: PrivateOfferUnlockCopy = {
  title: 'Private offer access',
  description: 'Enter a private access code.',
  codeLabel: 'Private access code',
  codePlaceholder: 'PRIVATE2026',
  unlockCta: 'Unlock offer',
  unlockingCta: 'Checking...',
  retryCta: 'Retry',
  clearCta: 'Clear private offer',
  availableLabel: 'Available by code',
  selectedLabel: 'Private offer selected',
  selectCta: 'Use this offer',
  previewOnlyHint: 'Sign in before checkout.',
  validationError: 'Enter a private access code first.',
  noOffers: 'This code does not unlock an active private offer for this store.',
  networkError: 'Private offer check could not reach the server.',
  authorizationError: 'Sign in again to check private offers.',
  genericError: 'Private offer check failed.',
  grantDegraded: 'Missing checkout grant.',
  grantExpired: 'This private offer preview expired.',
  unlocked: 'Private offer preview unlocked.',
  priceLabel: 'Private price',
  durationDays: (days) => `${days} days`,
  expiresAt: (date) => `Grant expires ${date}`,
  devices: (count) => `${count} devices`,
  traffic: (label) => `Traffic: ${label}`,
  modes: (modes) => `Modes: ${modes}`,
  serverPool: (servers) => `Servers: ${servers}`,
  support: (support) => `Support: ${support}`,
};

function renderUnlock(onSelectionChange = vi.fn()) {
  render(
    <PrivateOfferUnlock
      storefrontKey="cybervpn-web"
      channel="web"
      currency="USD"
      copy={copy}
      onSelectionChange={onSelectionChange}
    />,
  );
  return onSelectionChange;
}

function createPrivatePreflight(overrides: Record<string, unknown> = {}) {
  return {
    code_set_id: 'code-set-private',
    code_set_hash: 'hash-private',
    status: 'accepted',
    applications: [
      {
        client_slot_id: 'private-offer',
        masked_code: 'PRIV***',
        status: 'accepted',
        roles: ['private_catalog_access'],
        message_key: 'growth_codes.private.accepted',
      },
    ],
    private_catalog_grant: {
      id: PRIVATE_GRANT_ID,
      expires_at: '2099-04-18T12:00:00Z',
    },
    private_offers: [
      {
        plan_id: 'plan-private-90',
        offer_id: 'offer-private-90',
        display_name: 'Private 90',
        duration_days: 90,
        price: {
          amount: '19.00',
          currency: 'USD',
        },
        entitlement_summary: {
          device_limit: 3,
          display_traffic_label: 'Unlimited',
          connection_modes: ['stealth'],
          server_pool: ['premium'],
          support_sla: 'priority',
        },
        quote_handoff: {
          private_catalog_grant_id: PRIVATE_GRANT_ID,
        },
      },
    ],
    risk: {
      action: 'allow',
    },
    ...overrides,
  };
}

describe('PrivateOfferUnlock', () => {
  it('blocks empty private access codes before calling preflight', async () => {
    const user = userEvent.setup();
    const preflightSpy = vi.fn();

    server.use(
      http.post(API_V3_PREFLIGHT, () => {
        preflightSpy();
        return HttpResponse.json(createPrivatePreflight());
      }),
    );

    renderUnlock();

    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(copy.validationError);
    expect(preflightSpy).not.toHaveBeenCalled();
  });

  it('shows an empty state and no selectable offer when the grant has no private offers', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(API_V3_PREFLIGHT, () =>
        HttpResponse.json(createPrivatePreflight({ private_offers: [] }))),
    );

    renderUnlock();

    await user.type(screen.getByLabelText(copy.codeLabel), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));

    expect(await screen.findByText(copy.noOffers)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: copy.selectCta })).not.toBeInTheDocument();
  });

  it('does not render mismatched private offers without the matching quote handoff grant', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(API_V3_PREFLIGHT, () =>
        HttpResponse.json(createPrivatePreflight({
          private_offers: [
            {
              ...createPrivatePreflight().private_offers[0],
              quote_handoff: {
                private_catalog_grant_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
              },
            },
          ],
        }))),
    );

    renderUnlock();

    await user.type(screen.getByLabelText(copy.codeLabel), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));

    expect(await screen.findByText(copy.noOffers)).toBeInTheDocument();
    expect(screen.queryByText('Private 90')).not.toBeInTheDocument();
  });

  it('does not render expired private grants as selectable offers', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(API_V3_PREFLIGHT, () =>
        HttpResponse.json(createPrivatePreflight({
          private_catalog_grant: {
            id: PRIVATE_GRANT_ID,
            expires_at: '2000-04-18T12:00:00Z',
          },
        }))),
    );

    renderUnlock();

    await user.type(screen.getByLabelText(copy.codeLabel), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));

    expect(await screen.findByRole('status')).toHaveTextContent(copy.grantExpired);
    expect(screen.queryByRole('button', { name: copy.selectCta })).not.toBeInTheDocument();
  });

  it('shows authorization failures without rendering private offers', async () => {
    const user = userEvent.setup();

    server.use(
      http.post(API_V3_PREFLIGHT, () =>
        HttpResponse.json({ detail: 'forbidden' }, { status: 403 })),
    );

    renderUnlock();

    await user.type(screen.getByLabelText(copy.codeLabel), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(copy.authorizationError);
    expect(screen.queryByText('Private 90')).not.toBeInTheDocument();
  });

  it('lets the customer retry a network failure and select the allowed private offer', async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    let preflightCalls = 0;

    server.use(
      http.post(API_V3_PREFLIGHT, () => {
        preflightCalls += 1;
        if (preflightCalls === 1) {
          return HttpResponse.error();
        }
        return HttpResponse.json(createPrivatePreflight());
      }),
    );

    renderUnlock(onSelectionChange);

    await user.type(screen.getByLabelText(copy.codeLabel), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(copy.networkError);

    await user.click(screen.getByRole('button', { name: /Retry/ }));
    await user.click(await screen.findByRole('button', { name: copy.selectCta }));

    await waitFor(() => {
      expect(onSelectionChange).toHaveBeenLastCalledWith(
        expect.objectContaining({
          planId: 'plan-private-90',
          privateCatalogGrantId: PRIVATE_GRANT_ID,
        }),
      );
    });
    expect(preflightCalls).toBe(2);
  });

  it('clears selected grants when the private code changes', async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();

    server.use(
      http.post(API_V3_PREFLIGHT, () => HttpResponse.json(createPrivatePreflight())),
    );

    renderUnlock(onSelectionChange);

    await user.type(screen.getByLabelText(copy.codeLabel), 'private2026');
    await user.click(screen.getByRole('button', { name: 'Unlock offer' }));
    await user.click(await screen.findByRole('button', { name: copy.selectCta }));

    await waitFor(() => {
      expect(onSelectionChange).toHaveBeenLastCalledWith(
        expect.objectContaining({ privateCatalogGrantId: PRIVATE_GRANT_ID }),
      );
    });

    await user.type(screen.getByLabelText(copy.codeLabel), 'X');

    await waitFor(() => {
      expect(onSelectionChange).toHaveBeenLastCalledWith(null);
    });
    expect(screen.queryByText('Private 90')).not.toBeInTheDocument();
  });
});
