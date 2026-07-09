import fs from 'fs/promises';
import path from 'path';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';
import { Modal } from '../modal';

vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock('@/components/ui/InceptionButton', () => ({
  InceptionButton: ({ children }: { children: React.ReactNode }) => children,
}));

const ROOT = path.resolve(__dirname, '../../..');

async function readSource(relativePath: string) {
  return fs.readFile(path.join(ROOT, relativePath), 'utf-8');
}

describe('mobile touch target contract', () => {
  it('defines shared touch, form, and safe-area utilities in globals.css', async () => {
    const source = await readSource('app/globals.css');

    expect(source).toContain('.touch-target');
    expect(source).toContain('.touch-target-comfortable');
    expect(source).toContain('.mobile-form-input');
    expect(source).toContain('.keyboard-safe-bottom');
    expect(source).toContain('.safe-area-dialog');
    expect(source).toContain('.safe-area-scroll-panel');
    expect(source).toContain('@utility safe-inline-gutter');
    expect(source).toContain('@utility custom-scrollbar');
    expect(source).toContain('@utility no-scrollbar');
    expect(source).toContain(':root[dir="rtl"]');
    expect(source).toContain('--mobile-sidebar-hidden-x: 100%');
    expect(source).toContain('scrollbar-gutter: stable');
  });

  it('keeps dashboard chrome on logical layout and stable scrollbars', async () => {
    const layout = await readSource('app/[locale]/(dashboard)/layout.tsx');
    const desktopSidebar = await readSource('widgets/cyber-sidebar.tsx');
    const mobileSidebar = await readSource('widgets/mobile-sidebar.tsx');

    expect(layout).toContain('md:ps-64');
    expect(layout).toContain('safe-inline-gutter');
    expect(layout).toContain('scrollbar-gutter-stable');
    expect(layout).not.toContain('md:pl-64');

    for (const source of [desktopSidebar, mobileSidebar]) {
      expect(source).toContain('start-0');
      expect(source).toContain('border-e');
      expect(source).toContain('border-s-2');
      expect(source).toContain('custom-scrollbar');
      expect(source).toContain('scrollbar-gutter-stable');
      expect(source).toContain('rtl:-translate-x-1');
      expect(source).not.toContain('border-r ');
    }

    expect(mobileSidebar).toContain("x: 'var(--mobile-sidebar-hidden-x)'");
  });

  it('lets shared buttons opt into comfortable touch targets', () => {
    render(
      <Button
        {...({
          touchTarget: 'comfortable',
        } as Record<string, unknown>)}
      >
        Continue
      </Button>,
    );

    expect(screen.getByRole('button', { name: 'Continue' })).toHaveClass(
      'touch-target-comfortable',
    );
  });

  it('keeps modal shells inside safe areas and keyboard-safe padding', () => {
    render(
      <Modal isOpen onClose={() => {}} title="Safe area dialog">
        <button type="button">Focusable action</button>
      </Modal>,
    );

    expect(screen.getByRole('dialog')).toHaveClass('safe-area-dialog');
    expect(screen.getByText('Focusable action').parentElement).toHaveClass(
      'safe-area-scroll-panel',
      'keyboard-safe-bottom',
    );
  });

  it('routes high-risk forms through mobile-safe input sizing', async () => {
    const contact = await readSource('widgets/contact-form.tsx');
    const login = await readSource('app/[locale]/(auth)/login/login-client.tsx');

    expect(contact).toContain('mobile-form-input');
    expect(login).toContain('mobile-form-input');
  });
});
