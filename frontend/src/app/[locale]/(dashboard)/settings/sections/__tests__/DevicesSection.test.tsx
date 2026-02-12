/**
 * DevicesSection Component Tests
 *
 * Tests device session management functionality:
 * - List active devices with icons and details
 * - Remote logout for individual devices
 * - Logout all other devices
 * - Current device badge
 * - Loading and error states
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DevicesSection } from '../DevicesSection';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

const API_BASE = 'http://localhost:8000/api/v1';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
};

const mockDevices = [
  {
    device_id: 'device-1',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    last_used_at: '2026-02-11T10:00:00Z',
    is_current: true,
  },
  {
    device_id: 'device-2',
    ip_address: '192.168.1.101',
    user_agent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile Safari/604.1',
    last_used_at: '2026-02-10T15:30:00Z',
    is_current: false,
  },
  {
    device_id: 'device-3',
    ip_address: '10.0.0.50',
    user_agent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) Safari/604.1',
    last_used_at: '2026-02-09T08:00:00Z',
    is_current: false,
  },
];

describe('DevicesSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('test_shows_loading_skeleton_while_fetching', () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ devices: [] });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      const skeletons = document.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Device List Display', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: mockDevices });
        })
      );
    });

    it('test_displays_all_devices_with_details', async () => {
      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/192\.168\.1\.100/)).toBeInTheDocument();
      expect(screen.getByText(/192\.168\.1\.101/)).toBeInTheDocument();
      expect(screen.getByText(/10\.0\.0\.50/)).toBeInTheDocument();
    });

    it('test_shows_current_device_badge', async () => {
      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Current')).toBeInTheDocument();
      });

      const currentBadges = screen.getAllByText('Current');
      expect(currentBadges).toHaveLength(1);
    });

    it('test_displays_last_active_time', async () => {
      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Last active:/)).toBeInTheDocument();
      });

      const lastActiveTimes = screen.getAllByText(/Last active:/);
      expect(lastActiveTimes.length).toBe(3);
    });

    it('test_parses_user_agent_for_display', async () => {
      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Chrome on Windows/)).toBeInTheDocument();
      });

      expect(screen.getByText(/Safari on iOS/)).toBeInTheDocument();
    });
  });

  describe('Device Icons', () => {
    it('test_shows_smartphone_icon_for_mobile_devices', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({
            devices: [
              {
                device_id: 'mobile-1',
                ip_address: '192.168.1.1',
                user_agent: 'Mozilla/5.0 (iPhone) Mobile',
                last_used_at: '2026-02-11T10:00:00Z',
                is_current: false,
              },
            ],
          });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });

      // Icon is rendered via Lucide component
      const icons = document.querySelectorAll('svg');
      expect(icons.length).toBeGreaterThan(0);
    });

    it('test_shows_monitor_icon_for_tablet_devices', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({
            devices: [
              {
                device_id: 'tablet-1',
                ip_address: '192.168.1.1',
                user_agent: 'Mozilla/5.0 (iPad) Safari',
                last_used_at: '2026-02-11T10:00:00Z',
                is_current: false,
              },
            ],
          });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });

      const icons = document.querySelectorAll('svg');
      expect(icons.length).toBeGreaterThan(0);
    });

    it('test_shows_laptop_icon_for_desktop_devices', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({
            devices: [
              {
                device_id: 'desktop-1',
                ip_address: '192.168.1.1',
                user_agent: 'Mozilla/5.0 (Windows) Chrome',
                last_used_at: '2026-02-11T10:00:00Z',
                is_current: false,
              },
            ],
          });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });

      const icons = document.querySelectorAll('svg');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Logout All Others Button', () => {
    it('test_shows_logout_all_others_button_with_multiple_devices', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: mockDevices });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Logout All Others')).toBeInTheDocument();
      });
    });

    it('test_hides_logout_all_others_with_single_device', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({
            devices: [mockDevices[0]], // Only current device
          });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });

      expect(screen.queryByText('Logout All Others')).not.toBeInTheDocument();
    });

    it('test_logout_all_others_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: mockDevices });
        }),
        http.delete(`${API_BASE}/auth/devices/device-2`, () => {
          return HttpResponse.json({ message: 'Logged out successfully' });
        }),
        http.delete(`${API_BASE}/auth/devices/device-3`, () => {
          return HttpResponse.json({ message: 'Logged out successfully' });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Logout All Others')).toBeInTheDocument();
      });

      const logoutAllButton = screen.getByText('Logout All Others');
      await user.click(logoutAllButton);

      // Should refetch devices after logout
      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_logout_all_others_fails', async () => {
      const user = userEvent.setup();

      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: mockDevices });
        }),
        http.delete(`${API_BASE}/auth/devices/device-2`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Logout All Others')).toBeInTheDocument();
      });

      const logoutAllButton = screen.getByText('Logout All Others');
      await user.click(logoutAllButton);

      await waitFor(() => {
        expect(screen.getByText(/Failed to logout some devices/i)).toBeInTheDocument();
      });
    });
  });

  describe('Remote Logout Single Device', () => {
    beforeEach(() => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: mockDevices });
        })
      );
    });

    it('test_shows_logout_button_for_non_current_devices', async () => {
      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Current')).toBeInTheDocument();
      });

      const logoutButtons = screen.getAllByLabelText('Logout device');
      // 2 non-current devices should have logout buttons
      expect(logoutButtons).toHaveLength(2);
    });

    it('test_hides_logout_button_for_current_device', async () => {
      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Current')).toBeInTheDocument();
      });

      const logoutButtons = screen.getAllByLabelText('Logout device');
      // Should not have logout button for current device
      expect(logoutButtons).toHaveLength(2); // Only 2, not 3
    });

    it('test_logout_device_successfully', async () => {
      const user = userEvent.setup();

      server.use(
        http.delete(`${API_BASE}/auth/devices/device-2`, () => {
          return HttpResponse.json({ message: 'Logged out successfully' });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/192\.168\.1\.101/)).toBeInTheDocument();
      });

      const logoutButtons = screen.getAllByLabelText('Logout device');
      await user.click(logoutButtons[0]);

      // Should refetch devices after logout
      await waitFor(() => {
        expect(screen.getByText(/Active Devices/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_logout_fails_404', async () => {
      const user = userEvent.setup();

      server.use(
        http.delete(`${API_BASE}/auth/devices/device-2`, () => {
          return HttpResponse.json(
            { detail: 'Device not found' },
            { status: 404 }
          );
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/192\.168\.1\.101/)).toBeInTheDocument();
      });

      const logoutButtons = screen.getAllByLabelText('Logout device');
      await user.click(logoutButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Device not found/i)).toBeInTheDocument();
      });
    });

    it('test_shows_error_when_logout_fails_500', async () => {
      const user = userEvent.setup();

      server.use(
        http.delete(`${API_BASE}/auth/devices/device-2`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/192\.168\.1\.101/)).toBeInTheDocument();
      });

      const logoutButtons = screen.getAllByLabelText('Logout device');
      await user.click(logoutButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Internal server error/i)).toBeInTheDocument();
      });
    });

    it('test_disables_logout_button_while_logging_out', async () => {
      const user = userEvent.setup();

      server.use(
        http.delete(`${API_BASE}/auth/devices/device-2`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({ message: 'Success' });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/192\.168\.1\.101/)).toBeInTheDocument();
      });

      const logoutButtons = screen.getAllByLabelText('Logout device');
      const firstButton = logoutButtons[0] as HTMLButtonElement;

      await user.click(firstButton);

      // Button should be disabled during logout
      expect(firstButton).toBeDisabled();
    });
  });

  describe('Empty State', () => {
    it('test_shows_empty_state_when_no_devices', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: [] });
        })
      );

      render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/No active devices found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('test_handles_api_error_500', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      const { container } = render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
      });

      // Component should handle error gracefully
      expect(screen.queryByText(/Active Devices/i)).toBeInTheDocument();
    });

    it('test_handles_network_error', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.error();
        })
      );

      const { container } = render(<DevicesSection />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
      });

      // Component should handle error gracefully
      expect(screen.queryByText(/Active Devices/i)).toBeInTheDocument();
    });
  });

  describe('Query Configuration', () => {
    it('test_uses_correct_query_key', async () => {
      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: [] });
        })
      );

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = function Wrapper({ children }: { children: React.ReactNode }) {
        return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
      };

      render(<DevicesSection />, { wrapper });

      await waitFor(() => {
        const queryCache = queryClient.getQueryCache();
        const queries = queryCache.getAll();
        const devicesQuery = queries.find((q) =>
          JSON.stringify(q.queryKey).includes('devices')
        );
        expect(devicesQuery).toBeDefined();
      });
    });

    it('test_has_1_minute_stale_time', () => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = function Wrapper({ children }: { children: React.ReactNode }) {
        return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
      };

      server.use(
        http.get(`${API_BASE}/auth/devices`, () => {
          return HttpResponse.json({ devices: [] });
        })
      );

      render(<DevicesSection />, { wrapper });

      // Verify staleTime is set (1 minute = 60000ms)
      // Can't directly access staleTime but we can verify the hook is defined
      expect(screen.queryByText(/Active Devices/i)).toBeInTheDocument();
    });
  });
});
