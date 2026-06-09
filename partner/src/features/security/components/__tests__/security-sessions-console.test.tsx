import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SecuritySessionsConsole } from '../security-sessions-console';

const {
  mockListDevices,
  mockLogoutDevice,
  mockLogoutOtherDevices,
  mockLogoutAllDevices,
} = vi.hoisted(() => ({
  mockListDevices: vi.fn(),
  mockLogoutDevice: vi.fn(),
  mockLogoutOtherDevices: vi.fn(),
  mockLogoutAllDevices: vi.fn(),
}));

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    listDevices: (...args: unknown[]) => mockListDevices(...args),
    logoutDevice: (...args: unknown[]) => mockLogoutDevice(...args),
    logoutOtherDevices: (...args: unknown[]) => mockLogoutOtherDevices(...args),
    logoutAllDevices: (...args: unknown[]) => mockLogoutAllDevices(...args),
  },
}));

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

async function findEnabledButton(name: string, index = 0) {
  await screen.findAllByRole('button', { name });

  await waitFor(() => {
    expect(screen.getAllByRole('button', { name })[index]).toBeEnabled();
  });

  const button = screen.getAllByRole('button', { name })[index];
  if (!button) {
    throw new Error(`Button not found: ${name}`);
  }

  return button;
}

function createDeferredResponse<TData>() {
  let resolve!: (value: { data: TData }) => void;
  const promise = new Promise<{ data: TData }>((nextResolve) => {
    resolve = nextResolve;
  });

  return { promise, resolve };
}

function mockDeviceList() {
  mockListDevices.mockResolvedValue({
    data: {
      devices: [
        {
          device_id: 'dev_current',
          ip_address: '203.0.113.10',
          user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit Safari',
          last_used_at: '2026-04-10T08:00:00Z',
          created_at: '2026-04-09T08:00:00Z',
          is_current: true,
        },
        {
          device_id: 'dev_remote',
          ip_address: '198.51.100.77',
          user_agent: 'Mozilla/5.0 (Linux; Android 14) AppleWebKit Chrome',
          last_used_at: '2026-04-10T07:30:00Z',
          created_at: '2026-04-08T10:00:00Z',
          is_current: false,
        },
      ],
      total: 2,
      total_devices: 2,
      device_limit: 5,
      remaining_devices: 3,
    },
  });
}

describe('SecuritySessionsConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDeviceList();
  });

  it('uses backend unique-device totals and only renders one current badge', async () => {
    mockListDevices.mockResolvedValueOnce({
      data: {
        devices: [
          {
            device_id: 'dev_current',
            ip_address: '203.0.113.10',
            user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit Safari',
            last_used_at: '2026-04-10T08:00:00Z',
            created_at: '2026-04-09T08:00:00Z',
            is_current: true,
          },
          {
            device_id: 'dev_second_flag',
            ip_address: '203.0.113.11',
            user_agent: 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit Chrome',
            last_used_at: '2026-04-10T07:45:00Z',
            created_at: '2026-04-09T09:00:00Z',
            is_current: true,
          },
          {
            device_id: 'dev_remote',
            ip_address: '198.51.100.77',
            user_agent: 'Mozilla/5.0 (Linux; Android 14) AppleWebKit Chrome',
            last_used_at: '2026-04-10T07:30:00Z',
            created_at: '2026-04-08T10:00:00Z',
            is_current: false,
          },
        ],
        total: 3,
        total_devices: 4,
        device_limit: 5,
        remaining_devices: 1,
      },
    });

    renderWithQueryClient(<SecuritySessionsConsole />);

    expect(await screen.findByText('sessions.tableCaption')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('4/5')).toBeInTheDocument();
    expect(screen.getAllByText('common.current')).toHaveLength(1);
    expect(screen.getAllByText('sessions.currentDevice')).toHaveLength(1);
  });

  it('logs out other devices once even when confirm is clicked twice', async () => {
    const deferred = createDeferredResponse<{ message: string; sessions_revoked: number }>();
    mockLogoutOtherDevices.mockReturnValueOnce(deferred.promise);

    renderWithQueryClient(<SecuritySessionsConsole />);

    fireEvent.click(await findEnabledButton('common.logoutOthers'));
    const dialog = await screen.findByRole('dialog', {
      name: 'sessions.logoutOthersTitle',
    });
    const confirmButton = within(dialog).getByRole('button', {
      name: 'common.logoutOthers',
    });

    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockLogoutOtherDevices).toHaveBeenCalledTimes(1);
    });
    await act(async () => {
      deferred.resolve({
        data: {
          message: 'Other device sessions terminated',
          sessions_revoked: 1,
        },
      });
    });

    await waitFor(() => {
      expect(screen.getByText('sessions.logoutOthersSuccess')).toBeInTheDocument();
    });
  });

  it('revokes the selected device by stable device id once', async () => {
    const deferred = createDeferredResponse<{ message: string; device_id: string }>();
    mockLogoutDevice.mockReturnValueOnce(deferred.promise);

    renderWithQueryClient(<SecuritySessionsConsole />);

    fireEvent.click(await findEnabledButton('common.logoutDevice'));
    const dialog = await screen.findByRole('dialog', {
      name: 'sessions.revokeTitle',
    });
    const confirmButton = within(dialog).getByRole('button', {
      name: 'common.logoutDevice',
    });

    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockLogoutDevice).toHaveBeenCalledTimes(1);
      expect(mockLogoutDevice).toHaveBeenCalledWith('dev_remote');
    });
    await act(async () => {
      deferred.resolve({
        data: {
          message: 'Device session revoked successfully',
          device_id: 'dev_remote',
        },
      });
    });

    await waitFor(() => {
      expect(screen.getByText('Device session revoked successfully')).toBeInTheDocument();
    });
  });

  it('runs the hard-stop logout only once when confirm is clicked twice', async () => {
    const deferred = createDeferredResponse<{ message: string; sessions_revoked: number }>();
    mockLogoutAllDevices.mockReturnValueOnce(deferred.promise);

    renderWithQueryClient(<SecuritySessionsConsole />);

    fireEvent.click(await findEnabledButton('common.logoutAll'));
    const dialog = await screen.findByRole('dialog', {
      name: 'sessions.logoutAllTitle',
    });
    const confirmButton = within(dialog).getByRole('button', {
      name: 'common.logoutAll',
    });

    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockLogoutAllDevices).toHaveBeenCalledTimes(1);
    });
    await act(async () => {
      deferred.resolve({
        data: {
          message: 'All sessions terminated',
          sessions_revoked: 2,
        },
      });
    });

    await waitFor(() => {
      expect(window.location.assign).toHaveBeenCalledWith('/ru-RU/login');
    });
  });
});
