import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  getNodeDiagnostics,
  issueNodeSshTicket,
  requestPasskeyFreshAuthGrant,
  revokeNodeSshTicket,
} = vi.hoisted(() => ({
  getNodeDiagnostics: vi.fn(),
  issueNodeSshTicket: vi.fn(),
  requestPasskeyFreshAuthGrant: vi.fn(),
  revokeNodeSshTicket: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/features/auth/lib/passkey-fresh-auth', () => ({
  requestPasskeyFreshAuthGrant,
}));

vi.mock('@/lib/api/remnawave-status', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-status')>();
  return {
    ...actual,
    adminRemnawaveStatusApi: {
      ...actual.adminRemnawaveStatusApi,
      getNodeDiagnostics,
      issueNodeSshTicket,
      revokeNodeSshTicket,
    },
  };
});

import { RemnawaveNodeSshConsole } from './remnawave-node-ssh-console';

const NODE_ID = '00000000-0000-4000-8000-000000000020';
const TICKET = 'one_time_ticket_value_abcdefghijklmnopqrstuvwxyz_1234';

class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readonly protocols: string[];
  readyState = MockWebSocket.CONNECTING;
  sent: string[] = [];
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    this.protocols = typeof protocols === 'string' ? [protocols] : protocols ?? [];
    MockWebSocket.instances.push(this);
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  message(data: string) {
    this.onmessage?.(new MessageEvent('message', { data }));
  }

  error() {
    this.onerror?.(new Event('error'));
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }
}

function renderConsole(enabled = true) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RemnawaveNodeSshConsole enabled={enabled} />
    </QueryClientProvider>,
  );
}

async function startSession(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole('option', { name: 'Node Alpha · connected' });
  await user.selectOptions(screen.getByRole('combobox', { name: 'fields.node' }), NODE_ID);
  await user.type(
    screen.getByRole('textbox', { name: 'fields.reason' }),
    'Approved incident response',
  );
  await user.click(screen.getByRole('button', { name: 'connect' }));
  await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
  return MockWebSocket.instances[0]!;
}

describe('RemnawaveNodeSshConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    getNodeDiagnostics.mockResolvedValue({
      data: {
        nodes: [{
          uuid: NODE_ID,
          name: 'Node Alpha',
          status: 'connected',
          xhttp_enabled: true,
          tags: ['xhttp'],
        }],
        metrics_source: 'remnawave_api',
        updated_at: '2026-08-30T08:00:00Z',
        token_rotation_required: false,
      },
    });
    requestPasskeyFreshAuthGrant.mockResolvedValue('fresh-passkey-grant');
    issueNodeSshTicket.mockResolvedValue({
      data: {
        ticket: TICKET,
        node_uuid: NODE_ID,
        websocket_path: '/api/v1/admin/remnawave/node-ssh/ws',
        websocket_protocol: 'cybervpn-remnawave-ssh-v1',
        expires_in_seconds: 15,
      },
    });
    revokeNodeSshTicket.mockResolvedValue({ status: 204 });
  });

  it('does not request diagnostics or render controls when personalized SSH capability is false', () => {
    renderConsole(false);

    expect(screen.getByText('disabled')).toBeInTheDocument();
    expect(getNodeDiagnostics).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'connect' })).not.toBeInTheDocument();
  });

  it('uses fresh passkey auth and a same-origin one-time WebSocket without rendering the ticket', async () => {
    const user = userEvent.setup();
    renderConsole();
    const socket = await startSession(user);

    expect(requestPasskeyFreshAuthGrant).toHaveBeenCalledWith(
      `remnawave_node_ssh:issue:${NODE_ID}`,
    );
    expect(issueNodeSshTicket).toHaveBeenCalledWith(
      NODE_ID,
      'Approved incident response',
      { freshAuthGrantId: 'fresh-passkey-grant' },
    );
    expect(socket.url).toMatch(/^ws:\/\/localhost(?::\d+)?\/api\/v1\/admin\/remnawave\/node-ssh\/ws$/);
    expect(socket.protocols).toEqual(['cybervpn-remnawave-ssh-v1', TICKET]);
    expect(screen.queryByText(TICKET)).not.toBeInTheDocument();

    act(() => socket.open());
    expect(await screen.findByText('feedback.connected')).toBeInTheDocument();
    act(() => socket.message('\u001b[31mnode-ready\u001b[0m'));
    expect(await screen.findByText('node-ready')).toBeInTheDocument();

    await user.type(screen.getByRole('textbox', { name: 'fields.command' }), 'uptime');
    await user.click(screen.getByRole('button', { name: 'send' }));
    expect(socket.sent).toEqual(['uptime\n']);
    expect(screen.queryByDisplayValue('uptime')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'disconnect' }));
    await waitFor(() => {
      expect(revokeNodeSshTicket).toHaveBeenCalledWith(
        TICKET,
        'Admin requested disconnect',
      );
    });
    expect(await screen.findByText('feedback.revoked')).toBeInTheDocument();
  });

  it('closes and revokes a live session when the console unmounts', async () => {
    const user = userEvent.setup();
    const rendered = renderConsole();
    const socket = await startSession(user);
    act(() => socket.open());
    await screen.findByText('feedback.connected');

    rendered.unmount();

    await waitFor(() => {
      expect(revokeNodeSshTicket).toHaveBeenCalledWith(TICKET, 'Admin console unmounted');
    });
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it('fails closed and revokes the ticket when the relay errors', async () => {
    const user = userEvent.setup();
    renderConsole();
    const socket = await startSession(user);
    act(() => socket.open());
    await screen.findByText('feedback.connected');

    act(() => socket.error());

    expect(await screen.findByText('feedback.relayError')).toBeInTheDocument();
    await waitFor(() => {
      expect(revokeNodeSshTicket).toHaveBeenCalledWith(TICKET, 'Terminal relay failed');
    });
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it('shows a safe permission failure without opening a socket or exposing provider details', async () => {
    issueNodeSshTicket.mockRejectedValue({
      response: { status: 403, data: { detail: 'sensitive provider explanation' } },
    });
    const user = userEvent.setup();
    renderConsole();

    await screen.findByRole('option', { name: 'Node Alpha · connected' });
    await user.selectOptions(screen.getByRole('combobox', { name: 'fields.node' }), NODE_ID);
    await user.type(screen.getByRole('textbox', { name: 'fields.reason' }), 'Approved incident response');
    await user.click(screen.getByRole('button', { name: 'connect' }));

    expect(await screen.findByText('feedback.permissionDenied')).toBeInTheDocument();
    expect(MockWebSocket.instances).toHaveLength(0);
    expect(screen.queryByText('sensitive provider explanation')).not.toBeInTheDocument();
  });
});
