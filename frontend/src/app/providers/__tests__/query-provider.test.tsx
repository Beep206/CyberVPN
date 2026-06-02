import { render, screen } from '@testing-library/react';
import { useQueryClient } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';
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

  return (
    <div data-testid="query-client">
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
});
