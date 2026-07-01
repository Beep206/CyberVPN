import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const readSource = (path: string) =>
  readFileSync(resolve(process.cwd(), path), 'utf8');

describe('DevTools production safety gate', () => {
  it('requires an explicit public feature flag before rendering or bootstrapping', () => {
    const providerSource = readSource('src/app/providers/dev-tools.tsx');
    const bootstrapSource = readSource('src/app/providers/dev-tools-bootstrap.tsx');

    expect(providerSource).toContain('NEXT_PUBLIC_DEV_TOOLS_ENABLED');
    expect(bootstrapSource).toContain('NEXT_PUBLIC_DEV_TOOLS_ENABLED');
    expect(providerSource).toContain("process.env.NODE_ENV !== 'development'");
    expect(bootstrapSource).toContain("process.env.NODE_ENV !== 'development'");
  });

  it('cleans up temporary browser instrumentation on unmount', () => {
    const bootstrapSource = readSource('src/app/providers/dev-tools-bootstrap.tsx');

    expect(bootstrapSource).toContain('restoreTwaMock()');
    expect(bootstrapSource).toContain('consoleInterceptor.stop()');
    expect(bootstrapSource).toContain('networkLogger.stop()');
    expect(bootstrapSource).toContain('renderProfiler.stop()');
    expect(bootstrapSource).toContain('cssXRay.stop()');
  });
});
