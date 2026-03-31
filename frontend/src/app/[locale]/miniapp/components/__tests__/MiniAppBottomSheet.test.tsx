import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { Modal } from '@/shared/ui/modal';
import { MiniAppBottomSheet } from '../MiniAppBottomSheet';

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
});
