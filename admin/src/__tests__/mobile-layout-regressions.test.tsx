import fs from 'fs/promises';
import path from 'path';
import { describe, expect, it } from 'vitest';
import { MOBILE_ROUTE_CHECKLIST } from '@/test/mobile-route-checklist';
import { MOBILE_VIEWPORTS } from '@/test/mobile-viewport';

const ROOT = path.resolve(__dirname, '..');
const FRONTEND_ROOT = path.resolve(ROOT, '..');
const PROJECT_ROOT = path.resolve(FRONTEND_ROOT, '..');

async function readFrontendSource(relativePath: string) {
  return fs.readFile(path.join(ROOT, relativePath), 'utf-8');
}

async function readRepoFile(relativePath: string) {
  return fs.readFile(path.join(PROJECT_ROOT, relativePath), 'utf-8');
}

describe('mobile layout regression harness', () => {
  it('covers the required mobile viewport classes', () => {
    expect(Object.keys(MOBILE_VIEWPORTS)).toEqual([
      'iphoneSafari',
      'largeIphone',
      'androidChrome',
      'smallAndroid',
      'tabletPortrait',
      'tabletLandscape',
      'telegramWebView',
    ]);
  });

  it('covers the critical route inventory', () => {
    expect(MOBILE_ROUTE_CHECKLIST.map((entry) => entry.id)).toEqual([
      'dashboard-shell',
      'features',
      'pricing',
      'privacy',
      'download',
      'contact',
      'docs',
      'api',
    ]);
  });

  it('asserts the current mobile-safe source contracts for critical routes', async () => {
    for (const entry of MOBILE_ROUTE_CHECKLIST) {
      const sources = await Promise.all(
        entry.sourcePaths.map((sourcePath) => readFrontendSource(sourcePath)),
      );
      const combinedSource = sources.join('\n');

      for (const pattern of entry.mustContain) {
        expect(
          combinedSource,
          `Expected ${entry.id} to contain "${pattern}"`,
        ).toContain(pattern);
      }

      for (const pattern of entry.mustNotContain ?? []) {
        expect(
          combinedSource,
          `Expected ${entry.id} to avoid "${pattern}"`,
        ).not.toContain(pattern);
      }
    }
  });

  it('wires package scripts and budget automation for mobile release gates', async () => {
    const packageJson = JSON.parse(
      await fs.readFile(path.join(FRONTEND_ROOT, 'package.json'), 'utf-8'),
    ) as {
      scripts?: Record<string, string>;
    };
    const budgetScript = await readRepoFile(
      'frontend/scripts/mobile-performance-budget.mjs',
    );

    expect(packageJson.scripts?.['test:mobile-layout']).toBe(
      'vitest run src/__tests__/mobile-layout-regressions.test.tsx',
    );
    expect(packageJson.scripts?.['check:mobile-performance']).toBe(
      'node scripts/mobile-performance-budget.mjs',
    );
    expect(budgetScript).toContain('route-bundle-stats.json');
    expect(budgetScript).toContain('gzip');
  });

  it('documents automated mobile gates in the QA matrix and audit', async () => {
    const qaMatrix = await readRepoFile('docs/plans/2026-03-30-mobile-qa-matrix.md');
    const audit = await readRepoFile('docs/plans/2026-03-30-frontend-mobile-adaptation-audit.md');

    expect(qaMatrix).toContain('## Automated Gates');
    expect(qaMatrix).toContain('mobile-layout-regressions.test.tsx');
    expect(qaMatrix).toContain('mobile-performance-budget.mjs');
    expect(audit).toContain('Task 9 complete');
    expect(audit).toContain('mobile-layout-regressions.test.tsx');
    expect(audit).toContain('mobile-performance-budget.mjs');
  });
});
