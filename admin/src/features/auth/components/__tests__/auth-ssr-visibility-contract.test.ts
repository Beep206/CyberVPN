// @vitest-environment node

import fs from 'node:fs/promises';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = path.resolve(__dirname, '../../../..');

async function readSource(relativePath: string) {
  return fs.readFile(path.join(ROOT, relativePath), 'utf-8');
}

describe('Auth form SSR visibility contract', () => {
  it('does not server-render login-critical wrappers in an invisible initial state', async () => {
    const [cardSource, inputSource] = await Promise.all([
      readSource('features/auth/components/AuthFormCard.tsx'),
      readSource('features/auth/components/CyberInput.tsx'),
    ]);

    expect(cardSource).toContain('initial={false}');
    expect(cardSource).not.toContain('initial={{ opacity: 0');
    expect(inputSource).toMatch(/<motion\.div\s+initial=\{false\}/);
    expect(inputSource).not.toMatch(/<motion\.div\s+initial=\{\{\s*opacity:\s*0/);
  });
});
