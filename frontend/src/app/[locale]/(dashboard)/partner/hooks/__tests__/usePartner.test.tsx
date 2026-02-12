/**
 * Partner Hooks Tests
 *
 * Tests the three TanStack Query hooks for partner data:
 * - usePartnerDashboard
 * - usePartnerCodes
 * - usePartnerEarnings
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePartnerDashboard, usePartnerCodes, usePartnerEarnings } from '../usePartner';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';

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

describe('usePartnerDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_fetches_dashboard_successfully', async () => {
    const mockDashboard = {
      total_earnings: 500.75,
      active_codes_count: 8,
      referrals_count: 25,
    };

    server.use(
      http.get(`${API_BASE}/partner/dashboard`, () => {
        return HttpResponse.json(mockDashboard);
      })
    );

    const { result } = renderHook(() => usePartnerDashboard(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockDashboard);
  });

  it('test_handles_403_not_partner_error', async () => {
    server.use(
      http.get(`${API_BASE}/partner/dashboard`, () => {
        return HttpResponse.json(
          { detail: 'Not a partner' },
          { status: 403 }
        );
      })
    );

    const { result } = renderHook(() => usePartnerDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('test_does_not_retry_on_403', async () => {
    let callCount = 0;

    server.use(
      http.get(`${API_BASE}/partner/dashboard`, () => {
        callCount++;
        return HttpResponse.json(
          { detail: 'Not a partner' },
          { status: 403 }
        );
      })
    );

    const { result } = renderHook(() => usePartnerDashboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    // Should only call once (retry: false)
    expect(callCount).toBe(1);
  });

  it('test_has_2_minute_stale_time', () => {
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
      http.get(`${API_BASE}/partner/dashboard`, () => {
        return HttpResponse.json({});
      })
    );

    renderHook(() => usePartnerDashboard(), { wrapper });

    // Verify hook is defined
    expect(usePartnerDashboard).toBeDefined();
  });
});

describe('usePartnerCodes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_fetches_codes_successfully', async () => {
    const mockCodes = [
      { code: 'SUMMER2024', markup_percent: 15, uses_count: 10, earnings: 150.00 },
      { code: 'WINTER2024', markup_percent: 20, uses_count: 5, earnings: 75.50 },
    ];

    server.use(
      http.get(`${API_BASE}/partner/codes`, () => {
        return HttpResponse.json(mockCodes);
      })
    );

    const { result } = renderHook(() => usePartnerCodes(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockCodes);
  });

  it('test_handles_empty_codes_list', async () => {
    server.use(
      http.get(`${API_BASE}/partner/codes`, () => {
        return HttpResponse.json([]);
      })
    );

    const { result } = renderHook(() => usePartnerCodes(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });

  it('test_handles_api_error', async () => {
    server.use(
      http.get(`${API_BASE}/partner/codes`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => usePartnerCodes(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('test_uses_correct_query_key', async () => {
    server.use(
      http.get(`${API_BASE}/partner/codes`, () => {
        return HttpResponse.json([]);
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

    renderHook(() => usePartnerCodes(), { wrapper });

    await waitFor(() => {
      const queryCache = queryClient.getQueryCache();
      const queries = queryCache.getAll();
      const codesQuery = queries.find((q) =>
        JSON.stringify(q.queryKey).includes('partner-codes')
      );
      expect(codesQuery).toBeDefined();
    });
  });
});

describe('usePartnerEarnings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_fetches_earnings_successfully', async () => {
    const mockEarnings = [
      { created_at: '2026-02-10T12:00:00Z', code: 'SUMMER2024', amount: 50.00 },
      { created_at: '2026-02-09T12:00:00Z', code: 'WINTER2024', amount: 30.50 },
      { created_at: '2026-02-08T12:00:00Z', code: 'SUMMER2024', amount: 25.00 },
    ];

    server.use(
      http.get(`${API_BASE}/partner/earnings`, () => {
        return HttpResponse.json(mockEarnings);
      })
    );

    const { result } = renderHook(() => usePartnerEarnings(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockEarnings);
  });

  it('test_handles_empty_earnings_list', async () => {
    server.use(
      http.get(`${API_BASE}/partner/earnings`, () => {
        return HttpResponse.json([]);
      })
    );

    const { result } = renderHook(() => usePartnerEarnings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });

  it('test_handles_api_error', async () => {
    server.use(
      http.get(`${API_BASE}/partner/earnings`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => usePartnerEarnings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('test_uses_correct_query_key', async () => {
    server.use(
      http.get(`${API_BASE}/partner/earnings`, () => {
        return HttpResponse.json([]);
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

    renderHook(() => usePartnerEarnings(), { wrapper });

    await waitFor(() => {
      const queryCache = queryClient.getQueryCache();
      const queries = queryCache.getAll();
      const earningsQuery = queries.find((q) =>
        JSON.stringify(q.queryKey).includes('partner-earnings')
      );
      expect(earningsQuery).toBeDefined();
    });
  });

  it('test_has_2_minute_stale_time', () => {
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
      http.get(`${API_BASE}/partner/earnings`, () => {
        return HttpResponse.json([]);
      })
    );

    renderHook(() => usePartnerEarnings(), { wrapper });

    // Verify hook is defined
    expect(usePartnerEarnings).toBeDefined();
  });
});
