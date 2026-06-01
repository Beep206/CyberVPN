import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { Modal } from '@/shared/ui/modal';
import { MiniAppBottomSheet } from '../MiniAppBottomSheet';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

function OverlayHarness() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setIsModalOpen(true)}>
        Open modal
      </button>
      <button type="button" onClick={() => setIsSheetOpen(true)}>
        Open sheet
      </button>
      <button type="button" onClick={() => setIsModalOpen(false)}>
        Close modal
      </button>
      <button type="button" onClick={() => setIsSheetOpen(false)}>
        Close sheet
      </button>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Test modal">
        Modal content
      </Modal>

      <MiniAppBottomSheet
        isOpen={isSheetOpen}
        onClose={() => setIsSheetOpen(false)}
        title="Test sheet"
      >
        Sheet content
      </MiniAppBottomSheet>
    </>
  );
}

function FocusHarness() {
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setIsSheetOpen(true)}>
        Open focus sheet
      </button>
      <MiniAppBottomSheet
        isOpen={isSheetOpen}
        onClose={() => setIsSheetOpen(false)}
        title="Focus sheet"
      >
        <button type="button">Sheet action</button>
      </MiniAppBottomSheet>
    </>
  );
}

describe('MiniAppBottomSheet scroll lock', () => {
  beforeEach(() => {
    document.body.style.overflow = 'clip';
    document.documentElement.style.overflow = 'clip';
  });

  afterEach(() => {
    resetScrollLockForTests();
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
  });

  it('locks both document roots while the sheet is open', async () => {
    render(
      <MiniAppBottomSheet isOpen onClose={() => {}} title="Standalone sheet">
        Sheet body
      </MiniAppBottomSheet>
    );

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');
  });

  it('does not unlock document scroll while a modal still owns the lock', async () => {
    const user = userEvent.setup();

    render(<OverlayHarness />);

    await user.click(screen.getByRole('button', { name: 'Open modal' }));
    await user.click(screen.getByRole('button', { name: 'Open sheet' }));
    await user.click(screen.getByRole('button', { name: 'Close sheet' }));

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    await user.click(screen.getByRole('button', { name: 'Close modal' }));

    expect(document.body.style.overflow).toBe('clip');
    expect(document.documentElement.style.overflow).toBe('clip');
  });

  it('exposes dialog semantics and closes on Escape with focus returned', async () => {
    const user = userEvent.setup();

    render(<FocusHarness />);

    const trigger = screen.getByRole('button', { name: 'Open focus sheet' });
    await user.click(trigger);

    const dialog = await screen.findByRole('dialog', { name: 'Focus sheet' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: /close/i })).toHaveFocus();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('stacks the backdrop and sheet above fixed Mini App bottom navigation', () => {
    render(
      <>
        <nav aria-label="Bottom navigation" className="fixed bottom-0 z-50">
          Bottom nav
        </nav>
        <MiniAppBottomSheet isOpen onClose={() => {}} title="Stacked sheet">
          Sheet body
        </MiniAppBottomSheet>
      </>,
    );

    const backdrop = Array.from(
      document.querySelectorAll<HTMLElement>('[aria-hidden="true"]'),
    ).find((element) => element.classList.contains('inset-0'));

    if (!backdrop) {
      throw new Error('Bottom sheet backdrop was not rendered');
    }

    expect(screen.getByRole('navigation')).toHaveClass('z-50');
    expect(backdrop).toHaveClass('z-[60]');
    expect(screen.getByRole('dialog', { name: 'Stacked sheet' })).toHaveClass(
      'z-[70]',
    );
  });

  it('traps keyboard focus inside the sheet', async () => {
    const user = userEvent.setup();

    render(<FocusHarness />);
    await user.click(screen.getByRole('button', { name: 'Open focus sheet' }));

    const closeButton = await screen.findByRole('button', { name: /close/i });
    const actionButton = screen.getByRole('button', { name: 'Sheet action' });

    expect(closeButton).toHaveFocus();
    await user.tab();
    expect(actionButton).toHaveFocus();
    await user.tab();
    expect(closeButton).toHaveFocus();
    await user.tab({ shift: true });
    expect(actionButton).toHaveFocus();
  });
});
