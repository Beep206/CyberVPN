// @vitest-environment node

import fs from 'fs/promises';
import path from 'path';
import { describe, expect, it } from 'vitest';

const PROVIDER_PATH = path.resolve(__dirname, '../query-provider.tsx');

async function readQueryProvider() {
  return fs.readFile(PROVIDER_PATH, 'utf-8');
}

describe('QueryProvider source contract', () => {
  it('keeps React Query Devtools behind explicit public opt-in', async () => {
    const source = await readQueryProvider();

    expect(source).toContain('NEXT_PUBLIC_ENABLE_REACT_QUERY_DEVTOOLS');
    expect(source).toContain("process.env.NODE_ENV !== 'production'");
    expect(source).toContain(
      "process.env.NEXT_PUBLIC_ENABLE_REACT_QUERY_DEVTOOLS === 'true'",
    );
    expect(source).toContain('isReactQueryDevtoolsEnabled');
    expect(source).toContain('<QueryClientProvider client={queryClient}>');
    expect(source).toContain('{children}');
  });
});
