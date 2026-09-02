import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { createHost, listHosts, removeHost, updateHost } = vi.hoisted(() => ({
  createHost: vi.fn(),
  listHosts: vi.fn(),
  removeHost: vi.fn(),
  updateHost: vi.fn(),
}));

vi.mock('next-intl', () => ({ useTranslations: () => (key: string) => key }));
vi.mock('@/lib/api/infrastructure', () => ({
  hostsApi: { create: createHost, list: listHosts, remove: removeHost, update: updateHost },
}));

import { HostsConsole } from './hosts-console';

const host = {
  uuid: '550e8400-e29b-41d4-a716-446655440100',
  viewPosition: 1,
  remark: 'Edge primary',
  address: 'edge.example.test',
  port: 443,
  path: '/ws',
  sni: 'cloudflare.com',
  host: 'cloudflare.com',
  alpn: 'h2' as const,
  fingerprint: 'chrome',
  isDisabled: false,
  securityLayer: 'TLS' as const,
  xhttpExtraParams: null,
  muxParams: null,
  sockoptParams: null,
  finalMask: null,
  inbound: {
    configProfileUuid: '550e8400-e29b-41d4-a716-446655440000',
    configProfileInboundUuid: '550e8400-e29b-41d4-a716-446655440001',
  },
  serverDescription: null,
  tags: ['EDGE'],
  isHidden: false,
  overrideSniFromAddress: false,
  keepSniBlank: false,
  vlessRouteId: null,
  pinnedPeerCertSha256: null,
  verifyPeerCertByName: null,
  shuffleHost: false,
  mihomoX25519: false,
  mihomoIpVersion: null,
  nodes: [],
  xrayJsonTemplateUuid: null,
  excludeFromSubscriptionTypes: [],
  mapper: {},
  internalSquads: { mode: 'EXCLUDE' as const, squads: [] },
};

function renderConsole() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><HostsConsole /></QueryClientProvider>);
}

describe('HostsConsole Remnawave 3.4.3 boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listHosts.mockResolvedValue({ data: [host] });
    updateHost.mockResolvedValue({ data: undefined, status: 202 });
    removeHost.mockResolvedValue({ data: undefined, status: 204 });
  });

  it('keeps duplicate-prone creation visibly disabled', async () => {
    renderConsole();
    expect(await screen.findByText('Edge primary')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'hosts.createAction' })).toBeDisabled();
    expect(createHost).not.toHaveBeenCalled();
  });

  it('sends exact camelCase arrays and reports accepted-pending without claiming success', async () => {
    const user = userEvent.setup();
    renderConsole();
    await user.click(await screen.findByRole('button', { name: 'common.edit' }));

    const remark = screen.getByLabelText('hosts.fields.remark', { selector: 'input' });
    await user.clear(remark);
    await user.type(remark, 'Edge primary 3.4');
    const path = screen.getByLabelText('common.path', { selector: 'input' });
    await user.clear(path);
    await user.type(path, '/ws, /xhttp');
    await user.click(screen.getByRole('button', { name: 'common.save' }));

    await waitFor(() => expect(updateHost).toHaveBeenCalledTimes(1));
    expect(updateHost).toHaveBeenCalledWith(host.uuid, expect.objectContaining({
      remark: 'Edge primary 3.4',
      path: ['/ws', '/xhttp'],
      sni: ['cloudflare.com'],
      host: ['cloudflare.com'],
      alpn: 'h2',
      isDisabled: false,
      securityLayer: 'TLS',
      inbound: host.inbound,
      internalSquads: { mode: 'EXCLUDE', squads: [] },
    }));
    expect(await screen.findByRole('status')).toHaveTextContent('hosts.updatePending');
    expect(screen.queryByText('hosts.updateSuccess')).not.toBeInTheDocument();
  });

  it('shows a retryable error instead of treating a failed read as an empty list', async () => {
    listHosts.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: [host] });
    const user = userEvent.setup();
    renderConsole();

    expect(await screen.findByRole('alert')).toHaveTextContent('hosts.loadFailed');
    await user.click(screen.getByRole('button', { name: 'common.retry' }));
    expect(await screen.findByText('Edge primary')).toBeInTheDocument();
  });
});
