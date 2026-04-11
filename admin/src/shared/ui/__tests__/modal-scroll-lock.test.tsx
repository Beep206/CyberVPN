import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { resetScrollLockForTests } from '@/shared/lib/scroll-lock';
import { Modal } from '../modal';

function NestedModalHarness() {
  const [isFirstOpen, setIsFirstOpen] = useState(false);
  const [isSecondOpen, setIsSecondOpen] = useState(false);

  return (
    <>
      <button type="button" onClick={() => setIsFirstOpen(true)}>
        Open first modal
      </button>
      <button type="button" onClick={() => setIsSecondOpen(true)}>
        Open second modal
      </button>
      <button type="button" onClick={() => setIsFirstOpen(false)}>
        Close first modal
      </button>
      <button type="button" onClick={() => setIsSecondOpen(false)}>
        Close second modal
      </button>

      <Modal
        isOpen={isFirstOpen}
        onClose={() => setIsFirstOpen(false)}
        title="First modal"
      >
        First modal body
      </Modal>

      <Modal
        isOpen={isSecondOpen}
        onClose={() => setIsSecondOpen(false)}
        title="Second modal"
      >
        Second modal body
      </Modal>
    </>
  );
}

describe('Modal scroll lock', () => {
  beforeEach(() => {
    document.body.style.overflow = 'clip';
    document.documentElement.style.overflow = 'clip';
  });

  afterEach(() => {
    resetScrollLockForTests();
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
  });

  it('keeps document scroll locked until the last modal closes', async () => {
    const user = userEvent.setup();

    render(<NestedModalHarness />);

    await user.click(screen.getByRole('button', { name: 'Open first modal' }));

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    await user.click(screen.getByRole('button', { name: 'Open second modal' }));
    await user.click(screen.getByRole('button', { name: 'Close first modal' }));

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    await user.click(screen.getByRole('button', { name: 'Close second modal' }));

    expect(document.body.style.overflow).toBe('clip');
    expect(document.documentElement.style.overflow).toBe('clip');
  });

  it('restores previous overflow values when the final modal unmounts', () => {
    const onClose = vi.fn();
    const { unmount } = render(
      <Modal isOpen onClose={onClose} title="Unmount test">
        Modal body
      </Modal>
    );

    expect(document.body.style.overflow).toBe('hidden');
    expect(document.documentElement.style.overflow).toBe('hidden');

    unmount();

    expect(document.body.style.overflow).toBe('clip');
    expect(document.documentElement.style.overflow).toBe('clip');
  });
});
