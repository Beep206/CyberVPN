import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResponsiveSplitShell } from '../responsive-split-shell';

describe('ResponsiveSplitShell', () => {
  it('stacks primary content before heavy visuals on mobile by default', () => {
    render(
      <ResponsiveSplitShell
        header={<div>Header</div>}
        content={<div>Content</div>}
        visual={<div>Visual</div>}
      />
    );

    const body = screen.getByTestId('responsive-split-shell-body');
    const contentPane = screen.getByTestId('responsive-split-shell-content');
    const visualPane = screen.getByTestId('responsive-split-shell-visual');

    expect(Array.from(body.children)).toEqual([contentPane, visualPane]);
    expect(contentPane.className).toContain('order-1');
    expect(visualPane.className).toContain('order-2');
  });

  it('restores a desktop side-by-side layout contract', () => {
    render(
      <ResponsiveSplitShell
        header={<div>Header</div>}
        content={<div>Content</div>}
        visual={<div>Visual</div>}
      />
    );

    expect(screen.getByTestId('responsive-split-shell-body').className).toContain(
      'lg:grid-cols-12',
    );
  });

  it('pins visual panes only from the desktop breakpoint when requested', () => {
    render(
      <ResponsiveSplitShell
        header={<div>Header</div>}
        content={<div>Content</div>}
        visual={<div>Visual</div>}
        pinVisualOnDesktop
      />
    );

    const visualPane = screen.getByTestId('responsive-split-shell-visual');

    expect(visualPane.className).toContain('lg:sticky');
    expect(visualPane.className).toContain('lg:top-16');
    expect(visualPane.className.split(/\s+/)).not.toContain('sticky');
  });

  it('can opt into safe-area aware shell padding', () => {
    render(
      <ResponsiveSplitShell
        header={<div>Header</div>}
        content={<div>Content</div>}
        visual={<div>Visual</div>}
        safeAreaPadding
      />
    );

    const shell = screen.getByTestId('responsive-split-shell-container');

    expect(shell.className).toContain('pt-[calc(var(--safe-area-top)+1rem)]');
    expect(shell.className).toContain('pb-[calc(var(--safe-area-bottom)+1.5rem)]');
  });

  it('supports background visuals without making them mobile scroll owners', () => {
    render(
      <ResponsiveSplitShell
        header={<div>Header</div>}
        content={<div>Content</div>}
        visual={<div>Visual</div>}
        visualMode="background"
      />
    );

    const visualPane = screen.getByTestId('responsive-split-shell-visual');

    expect(visualPane.className).toContain('lg:absolute');
    expect(visualPane.className).toContain('lg:inset-0');
    expect(visualPane.className.split(/\s+/)).not.toContain('sticky');
  });
});
