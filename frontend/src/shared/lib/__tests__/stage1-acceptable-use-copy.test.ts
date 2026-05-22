import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import enAcceptableUse from '../../../../messages/en-EN/AcceptableUse.json';
import enFooter from '../../../../messages/en-EN/footer.json';
import ruAcceptableUse from '../../../../messages/ru-RU/AcceptableUse.json';
import ruFooter from '../../../../messages/ru-RU/footer.json';

type Messages = Record<string, unknown>;

const requiredPhrases = [
  'public release 1.0',
  'abuse@cyber-vpn.net',
  'support@cyber-vpn.net',
  'spam',
  'phishing',
  'credential stuffing',
  'malware',
  'ransomware',
  'ddos',
  'port scanning',
  'scraping',
  'child sexual abuse material',
  'minors',
  'torrent',
  'p2p',
  'node',
  'provider',
  'subscription urls',
  'qr codes',
  'rate limit',
  'suspend',
  'refund policy',
];

const unsafePhrases = [
  'torrenting is allowed everywhere',
  'p2p is allowed everywhere',
  'unlimited bandwidth',
  'no restrictions',
  'no limits',
  'without explanation',
  'for any reason',
  'permanent action without evidence',
  'strict no-log policy',
  'physically incapable of storing',
  'cannot surrender what we do not possess',
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

describe('stage2 acceptable use policy copy', () => {
  it('states required S2 AUP abuse, network and reporting controls', () => {
    const combined = `${flattenMessages(enAcceptableUse)}\n${flattenMessages(ruAcceptableUse)}`.toLowerCase();

    for (const phrase of requiredPhrases) {
      expect(combined).toContain(phrase);
    }
  });

  it('adds footer navigation to the acceptable use page', () => {
    expect(enFooter.links.acceptableUse).toBe('Acceptable Use');
    expect(ruFooter.links.acceptableUse).toBe('Правила использования');
  });

  it('keeps torrent and enforcement wording bounded by node/provider evidence', () => {
    const text = flattenMessages(enAcceptableUse).toLowerCase();

    expect(text).toContain('does not promise that torrent or p2p traffic is available on every node');
    expect(text).toContain('provider policy');
    expect(text).toContain('operational evidence');
    expect(text).toContain('avoid permanent action without enough evidence');
  });

  it('removes unsafe AUP phrases from all locale copies', () => {
    const localeFiles = [
      ...readLocaleFile('AcceptableUse.json'),
      ...readLocaleFile('footer.json'),
    ];

    for (const { locale, messages } of localeFiles) {
      const text = flattenMessages(messages);

      for (const phrase of unsafePhrases) {
        expect(text, `${locale} contains unsafe phrase: ${phrase}`).not.toContain(phrase);
      }
    }
  });
});
