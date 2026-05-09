import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import enPrivacy from '../../../../messages/en-EN/Privacy.json';
import enPolicy from '../../../../messages/en-EN/privacy-policy.json';
import ruPrivacy from '../../../../messages/ru-RU/Privacy.json';
import ruPolicy from '../../../../messages/ru-RU/privacy-policy.json';

type Messages = Record<string, unknown>;

const unsafePhrases = [
  '[Your Company Address]',
  'privacy@cybervpn.app',
  'strict no-log policy',
  'No connection timestamps or session duration',
  'No DNS queries or IP addresses',
  'End-to-end encryption for all VPN traffic',
  'Payment processing (Stripe, cryptocurrency gateways)',
  'physically incapable of storing',
  'cannot surrender what we do not possess',
  'RAM disks',
  'quantum computer',
  'TOP SECRET',
];

function flattenMessages(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(flattenMessages).join('\n');
  }

  if (typeof value === 'object' && value !== null) {
    return Object.values(value).map(flattenMessages).join('\n');
  }

  return '';
}

function readLocaleFile(fileName: string): Array<{ locale: string; messages: Messages }> {
  const messagesRoot = join(process.cwd(), 'messages');

  return readdirSync(messagesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .filter((entry) => existsSync(join(messagesRoot, entry.name, fileName)))
    .map((entry) => {
      const filePath = join(messagesRoot, entry.name, fileName);
      const messages = JSON.parse(readFileSync(filePath, 'utf8')) as Messages;

      return { locale: entry.name, messages };
    });
}

describe('stage1 privacy policy copy', () => {
  it('states S1 data categories, retention criteria and privacy contact', () => {
    const policyText = `${flattenMessages(enPolicy)}\n${flattenMessages(ruPolicy)}`;
    const summaryText = `${flattenMessages(enPrivacy)}\n${flattenMessages(ruPrivacy)}`;
    const combined = `${policyText}\n${summaryText}`.toLowerCase();

    expect(combined).toContain('controlled public beta');
    expect(combined).toContain('privacy@cyber-vpn.net');
    expect(combined).toContain('individual founder/owner');
    expect(combined).toContain('telegram');
    expect(combined).toContain('oauth');
    expect(combined).toContain('remnawave');
    expect(combined).toContain('ip address');
    expect(combined).toContain('user-agent');
    expect(combined).toContain('payment providers');
    expect(combined).toContain('support tickets');
    expect(combined).toContain('postgresql backups');
    expect(combined).toContain('30 days');
    expect(combined).toContain('14 days');
    expect(combined).toContain('90 days');
  });

  it('removes unsafe legacy privacy policy phrases from all locales', () => {
    const localeFiles = [
      ...readLocaleFile('privacy-policy.json'),
      ...readLocaleFile('Privacy.json'),
      ...readLocaleFile('delete-account.json'),
    ];

    for (const { locale, messages } of localeFiles) {
      const text = flattenMessages(messages);

      for (const phrase of unsafePhrases) {
        expect(text, `${locale} contains unsafe phrase: ${phrase}`).not.toContain(phrase);
      }
    }
  });

  it('keeps no-logs wording bounded instead of absolute', () => {
    const text = flattenMessages(enPolicy).toLowerCase();

    expect(text).toContain('do not treat this as a final audited no-logs claim');
    expect(text).toContain('must be validated against backend logs');
    expect(text).toContain('vpn node logs');
    expect(text).toContain('observability tools');
  });
});
