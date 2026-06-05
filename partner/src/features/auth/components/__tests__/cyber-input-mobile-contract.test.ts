// @vitest-environment node

import fs from 'node:fs/promises';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = path.resolve(__dirname, '../../../..');

async function readSource(relativePath: string) {
  return fs.readFile(path.join(ROOT, relativePath), 'utf-8');
}

describe('CyberInput mobile layout contract', () => {
  it('keeps login adornments bounded and exposes keyboard focus-visible styling', async () => {
    const source = await readSource('features/auth/components/CyberInput.tsx');

    expect(source).toContain('relative flex min-w-0 items-center overflow-hidden');
    expect(source).toContain('has-[:focus-visible]:ring-2');
    expect(source).toContain('has-[:focus-visible]:ring-offset-terminal-bg');
    expect(source).toContain('shrink-0 pl-3 pr-1.5');
    expect(source).toContain('min-w-0 flex-1');
    expect(source).toContain('focus-visible:ring-2');
    expect(source).toContain('touch-target inline-flex w-11 shrink-0');
    expect(source).not.toContain('tabIndex={-1}');
  });
});
