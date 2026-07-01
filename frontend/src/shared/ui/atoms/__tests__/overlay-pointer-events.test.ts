import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const readSource = (path: string) =>
  readFileSync(resolve(process.cwd(), path), 'utf8');

describe('decorative overlay pointer-events contract', () => {
  it('marks shared scanline overlays as decorative and non-interactive', () => {
    const source = readSource('src/shared/ui/atoms/scanlines.tsx');

    expect(source).toContain('data-cy-overlay="decorative"');
    expect(source).toContain('pointer-events-none');
  });

  it('keeps global decorative overlays unable to intercept cabinet clicks', () => {
    const css = readSource('src/app/globals.css');
    const globeSource = readSource(
      'src/app/[locale]/(dashboard)/dashboard/components/DashboardGlobe.tsx',
    );

    expect(css).toContain("[data-cy-overlay='decorative']");
    expect(css).toContain("[data-cy-overlay='dashboard-globe']");
    expect(css).toContain('pointer-events: none !important');
    expect(globeSource).toContain('data-cy-overlay="dashboard-globe"');
  });
});
