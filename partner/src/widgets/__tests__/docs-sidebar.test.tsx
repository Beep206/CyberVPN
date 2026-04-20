import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DocsSidebar } from '../docs-sidebar';

describe('DocsSidebar', () => {
  const originalScrollTo = window.scrollTo;
  const scrollIntoView = vi.fn();

  beforeEach(() => {
    scrollIntoView.mockReset();
    window.scrollTo = vi.fn();
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
      writable: true,
    });
  });

  afterEach(() => {
    window.scrollTo = originalScrollTo;
  });

  it('scrolls the active anchor into view instead of hard-coding window scroll ownership', async () => {
    const user = userEvent.setup();
    const onSectionChange = vi.fn();
    const anchor = document.createElement('section');

    anchor.id = 'routing';
    document.body.appendChild(anchor);

    render(
      <DocsSidebar
        activeSection="getting_started"
        onSectionChange={onSectionChange}
      />
    );

    await user.click(screen.getByRole('link', { name: 'section_routing' }));

    expect(onSectionChange).toHaveBeenCalledWith('routing');
    expect(scrollIntoView).toHaveBeenCalled();
    expect(window.scrollTo).not.toHaveBeenCalled();

    anchor.remove();
  });
});
