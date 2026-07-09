import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useEffect, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ActivityDevTabPanel,
  buildDevActivityMarkName,
  markDevActivityTabVisible,
} from '../activity-dev-tab-panel';

function EffectfulCounter({
  onCleanup,
  onMount,
}: {
  onCleanup: () => void;
  onMount: () => void;
}) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    onMount();
    return onCleanup;
  }, [onCleanup, onMount]);

  return (
    <button type="button" onClick={() => setCount((current) => current + 1)}>
      Count {count}
    </button>
  );
}

describe('ActivityDevTabPanel', () => {
  afterEach(() => {
    performance.clearMarks();
  });

  it('hides inactive dev tabs with React Activity while preserving local state', async () => {
    const onMount = vi.fn();
    const onCleanup = vi.fn();
    const { rerender } = render(
      <ActivityDevTabPanel active tabId="performance">
        <EffectfulCounter onCleanup={onCleanup} onMount={onMount} />
      </ActivityDevTabPanel>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Count 0' }));
    expect(screen.getByRole('button', { name: 'Count 1' })).toBeVisible();

    rerender(
      <ActivityDevTabPanel active={false} tabId="performance">
        <EffectfulCounter onCleanup={onCleanup} onMount={onMount} />
      </ActivityDevTabPanel>,
    );

    await waitFor(() => expect(onCleanup).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole('button', { name: /Count/ })).toBeNull();

    rerender(
      <ActivityDevTabPanel active tabId="performance">
        <EffectfulCounter onCleanup={onCleanup} onMount={onMount} />
      </ActivityDevTabPanel>,
    );

    expect(screen.getByRole('button', { name: 'Count 1' })).toBeVisible();
    expect(onMount).toHaveBeenCalledTimes(2);
  });

  it('emits safe static performance marks for React performance track correlation', () => {
    markDevActivityTabVisible('performance');
    markDevActivityTabVisible('../operator@example.com');

    expect(performance.getEntriesByName(buildDevActivityMarkName('performance'))).toHaveLength(1);
    expect(performance.getEntriesByName(buildDevActivityMarkName('../operator@example.com'))).toHaveLength(1);
    expect(buildDevActivityMarkName('../operator@example.com')).toBe(
      'cybervpn.dev_panel.activity_tab.unknown.visible',
    );
  });
});
