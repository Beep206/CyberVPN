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
    const login = await readSource('app/[locale]/(auth)/login/page.tsx');
    const register = await readSource('app/[locale]/(auth)/register/page.tsx');
    const forgotPassword = await readSource('app/[locale]/(auth)/forgot-password/page.tsx');

    expect(contact).toContain('mobile-form-input');
    expect(login).toContain('mobile-form-input');
    expect(register).toContain('mobile-form-input');
    expect(forgotPassword).toContain('mobile-form-input');
  });
});
