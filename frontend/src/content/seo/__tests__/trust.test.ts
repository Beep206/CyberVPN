import { describe, expect, it, vi } from 'vitest';
import { getAuditsContent, getTrustCenterContent } from '../trust';

vi.mock('next/cache', () => ({
  cacheLife: vi.fn(),
  cacheTag: vi.fn(),
}));

describe('trust SEO content', () => {
  it('keeps trust center claims bounded and routes evidence to public support surfaces', async () => {
    const page = await getTrustCenterContent('en-EN');
    const allCopy = [
      page.title,
      page.description,
      ...page.heroPoints,
      ...page.sections.flatMap((section) => [
        section.title,
        ...section.paragraphs,
        ...(section.bullets ?? []),
      ]),
    ].join(' ');

    expect(page.path).toBe('/trust');
    expect(page.badge).toBe('Trust center');
    expect(page.relatedLinks.map((link) => link.href)).toEqual([
      '/audits',
      '/security',
      '/status',
    ]);
    expect(page.ctaLinks.map((link) => link.seoCta)).toEqual([
      'trust_audits',
      'trust_security',
      'trust_help',
    ]);
    expect(allCopy).toContain('Do not make logging claims that support workflows cannot defend');
    expect(allCopy).toContain('billing, support, security, and abuse handling');
    expect(allCopy.toLowerCase()).not.toContain('guaranteed no logs');
    expect(allCopy.toLowerCase()).not.toContain('audited no-logs certified');
  });

  it('keeps audits copy explicit about unavailable external verification', async () => {
    const page = await getAuditsContent('en-EN');
    const sectionTitles = page.sections.map((section) => section.title);
    const allCopy = [
      page.title,
      page.description,
      ...page.heroPoints,
      ...page.sections.flatMap((section) => [
        section.title,
        ...section.paragraphs,
        ...(section.bullets ?? []),
      ]),
    ].join(' ');

    expect(page.path).toBe('/audits');
    expect(sectionTitles).toEqual([
      'What an audit should answer',
      'How to evaluate evidence quality',
      'How audits feed operations',
    ]);
    expect(page.relatedLinks.map((link) => link.href)).toEqual([
      '/trust',
      '/help',
      '/contact',
    ]);
    expect(page.ctaLinks.map((link) => link.seoZone)).toEqual([
      'audits_content',
      'audits_content',
      'audits_content',
    ]);
    expect(allCopy).toContain('Screenshots and vague claims are not evidence');
    expect(allCopy).toContain('State the scope and date clearly');
    expect(allCopy.toLowerCase()).not.toContain('soc 2 certified');
    expect(allCopy.toLowerCase()).not.toContain('third-party audit completed');
  });

  it('falls back unsupported locales to the default market copy without changing canonical routes', async () => {
    const trustPage = await getTrustCenterContent('zz-ZZ');
    const auditsPage = await getAuditsContent('zz-ZZ');

    expect(trustPage.path).toBe('/trust');
    expect(trustPage.title).toBe('CyberVPN trust center');
    expect(auditsPage.path).toBe('/audits');
    expect(auditsPage.title).toBe('CyberVPN audit and verification posture');
  });
});
