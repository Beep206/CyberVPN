import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TerminalHeader } from '../terminal-header';

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: string) => key),
}));

vi.mock('@/widgets/mobile-sidebar', () => ({
  MobileSidebar: () => (
    <button type="button" aria-label="openMenu" aria-haspopup="dialog">
      menu
    </button>
  ),
}));

vi.mock('@/widgets/terminal-header-performance', () => ({
  TerminalHeaderPerformance: ({
    fpsLabel,
    pingLabel,
  }: {
    fpsLabel: string;
    pingLabel: string;
  }) => (
    <div data-testid="terminal-header-performance">
      {fpsLabel}:{pingLabel}
    </div>
  ),
}));

vi.mock('@/widgets/terminal-header-controls', () => ({
  TerminalHeaderControls: () => <div data-testid="terminal-header-controls">controls</div>,
}));

describe('TerminalHeader', () => {
  async function renderHeader() {
    render(
      await TerminalHeader({ performanceMode: 'always', showMobileSidebar: true })
    );
  }

  it('renders the async header shell with a single mobile navigation trigger', async () => {
    await renderHeader();

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'openMenu' })).toHaveLength(1);
  });

  it('renders performance and control regions with translated labels', async () => {
    await renderHeader();

    expect(screen.getByTestId('terminal-header-performance')).toHaveTextContent(
      'fps:ping',
    );
    expect(screen.getByTestId('terminal-header-controls')).toHaveTextContent('controls');
  });

  it('keeps the uplink status badge in the header flow', async () => {
    await renderHeader();

    expect(screen.getByText('netUplink')).toBeInTheDocument();
  });
});
