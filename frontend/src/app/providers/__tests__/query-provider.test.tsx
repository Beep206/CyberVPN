import { render, screen } from '@testing-library/react';
import { useQueryClient } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  MUTATION_GC_TIME_MS,
  QUERY_GC_TIME_MS,
  QUERY_STALE_TIME_MS,
  exponentialRetryDelay,
  queryClientDefaultOptions,
  shouldRetryQuery,
} from '../query-client-policy';
import { QueryProvider } from '../query-provider';

const devtoolsRender = vi.hoisted(() => vi.fn());

vi.mock('next/dynamic', () => ({
  default: () => {
    function MockReactQueryDevtools() {
      devtoolsRender();
      return <div data-testid="react-query-devtools" />;
    }

    return MockReactQueryDevtools;
  },
}));

function QueryClientProbe() {
  const queryClient = useQueryClient();
  const defaultOptions = queryClient.getDefaultOptions();

  return (
    <div
      data-testid="query-client"
      data-mutation-gc-time={String(defaultOptions.mutations?.gcTime)}
      data-mutation-retry={String(defaultOptions.mutations?.retry)}
      data-query-gc-time={String(defaultOptions.queries?.gcTime)}
      data-query-stale-time={String(defaultOptions.queries?.staleTime)}
    >
      {queryClient ? 'ready' : 'missing'}
    </div>
  );
}

describe('QueryProvider', () => {
  afterEach(() => {
    devtoolsRender.mockClear();
  });

  it('provides query client context without mounting devtools by default', () => {
    render(
      <QueryProvider>
        <QueryClientProbe />
      </QueryProvider>,
    );

    expect(screen.getByTestId('query-client')).toHaveTextContent('ready');
    expect(screen.getByTestId('query-client')).toHaveAttribute(
      'data-query-stale-time',
      String(QUERY_STALE_TIME_MS),
    );
    expect(screen.getByTestId('query-client')).toHaveAttribute(
      'data-query-gc-time',
      String(QUERY_GC_TIME_MS),
    );
    expect(screen.getByTestId('query-client')).toHaveAttribute(
      'data-mutation-retry',
      'false',
    );
    expect(screen.getByTestId('query-client')).toHaveAttribute(
      'data-mutation-gc-time',
      String(MUTATION_GC_TIME_MS),
    );
    expect(screen.queryByTestId('react-query-devtools')).not.toBeInTheDocument();
    expect(devtoolsRender).not.toHaveBeenCalled();
  });

  it('keeps React Query devtools behind explicit opt-in', () => {
    render(
      <QueryProvider showDevtools>
        <QueryClientProbe />
      </QueryProvider>,
    );

    expect(screen.getByTestId('query-client')).toHaveTextContent('ready');
    expect(screen.getByTestId('react-query-devtools')).toBeInTheDocument();
    expect(devtoolsRender).toHaveBeenCalledOnce();
  });

  it('fails fast for client errors and retries only bounded transient query failures', () => {
    expect(queryClientDefaultOptions.mutations?.retry).toBe(false);
    expect(queryClientDefaultOptions.mutations?.gcTime).toBe(MUTATION_GC_TIME_MS);

    expect(shouldRetryQuery(0, { response: { status: 401 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 403 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 404 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 429 } })).toBe(false);
    expect(shouldRetryQuery(0, { response: { status: 500 } })).toBe(true);
    expect(shouldRetryQuery(1, new TypeError('network failed'))).toBe(true);
    expect(shouldRetryQuery(2, new TypeError('network failed'))).toBe(false);
    expect(exponentialRetryDelay(0)).toBe(1_000);
    expect(exponentialRetryDelay(4)).toBe(10_000);
  });
});
