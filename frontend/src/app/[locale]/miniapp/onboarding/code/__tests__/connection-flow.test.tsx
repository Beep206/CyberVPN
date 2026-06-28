import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MiniAppOnboardingCodePage from '../page';

const { promptMock } = vi.hoisted(() => ({
  promptMock: vi.fn(({ surface }: { surface: string }) => (
    <div data-testid="post-registration-prompt" data-surface={surface}>
      onboarding prompt
    </div>
  )),
}));

vi.mock('@/features/customer-onboarding/PostRegistrationGrowthCodePrompt', () => ({
  PostRegistrationGrowthCodePrompt: promptMock,
}));

describe('MiniAppOnboardingCodePage', () => {
  it('mounts the shared onboarding prompt with the Mini App surface', () => {
    render(<MiniAppOnboardingCodePage />);

    const prompt = screen.getByTestId('post-registration-prompt');
    expect(prompt).toHaveAttribute('data-surface', 'miniapp');
    expect(promptMock.mock.calls[0][0]).toEqual(expect.objectContaining({ surface: 'miniapp' }));
  });
});
