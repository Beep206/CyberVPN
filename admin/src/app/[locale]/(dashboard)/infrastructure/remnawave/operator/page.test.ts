import { describe, expect, it, vi } from 'vitest';

vi.mock(
  '@/features/infrastructure/components/remnawave-operator-console',
  () => ({ RemnawaveOperatorConsole: vi.fn() }),
);

import InfrastructureRemnawaveOperatorPage from './page';

describe('InfrastructureRemnawaveOperatorPage', () => {
  it('selects root snippets for migrated legacy URLs', async () => {
    const page = await InfrastructureRemnawaveOperatorPage({
      searchParams: Promise.resolve({ section: 'snippets' }),
    });

    expect(page.props).toMatchObject({ initialSection: 'snippets' });
  });

  it('fails closed to tags for an unknown section', async () => {
    const page = await InfrastructureRemnawaveOperatorPage({
      searchParams: Promise.resolve({ section: 'unknown' }),
    });

    expect(page.props).toMatchObject({ initialSection: 'tags' });
  });
});
