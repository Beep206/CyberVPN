import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import enDeleteAccount from '../../../../messages/en-EN/delete-account.json';
import enFooter from '../../../../messages/en-EN/footer.json';
import enRefundPolicy from '../../../../messages/en-EN/RefundPolicy.json';
import ruDeleteAccount from '../../../../messages/ru-RU/delete-account.json';
import ruFooter from '../../../../messages/ru-RU/footer.json';
import ruRefundPolicy from '../../../../messages/ru-RU/RefundPolicy.json';

type Messages = Record<string, unknown>;

const requiredPhrases = [
  'public release 1.0',
  'refund@cyber-vpn.net',
  'payram',
  'nowpayments',
  'cryptobot',
  'telegram stars',
  'digiseller',
  'yookassa',
  'finance/support review',
  'paid-but-no-access',
  '24 hours',
  'no automatic refund is promised',
  'refundstarpayment',
  '/paysupport',
  'idempotency',
  'cvv/cvc',
  'raw subscription urls',
  'raw vpn configuration files',
  'acceptable use policy',
  'privacy policy',
];

const unsafePhrases = [
  'guaranteed refund',
  'automatic refund is guaranteed',
  'automatic refund will be issued',
  'instant refund',
  'refunds are always available',
  'refunds are never available',
  '(no refunds)',
  'no refunds)',
  'without review',
  'no questions asked',
  'full refund for any reason',
  'chargeback is automatic',
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

describe('stage2 refund policy copy', () => {
  it('states required S2 refund contacts, provider rules and review constraints', () => {
    const combined = `${flattenMessages(enRefundPolicy)}\n${flattenMessages(ruRefundPolicy)}`.toLowerCase();

    for (const phrase of requiredPhrases) {
      expect(combined).toContain(phrase);
    }
  });

  it('adds footer navigation to the refund policy page', () => {
    expect(enFooter.links.refundPolicy).toBe('Refund Policy');
    expect(ruFooter.links.refundPolicy).toBe('Политика возвратов');
  });

  it('keeps account deletion copy aligned with refund policy review', () => {
    const combined = `${flattenMessages(enDeleteAccount)}\n${flattenMessages(ruDeleteAccount)}`.toLowerCase();

    expect(combined).toContain('refund policy');
    expect(combined).toContain('provider rules');
    expect(combined).not.toContain('(no refunds)');
  });

  it('removes unsafe refund promises from all locale copies', () => {
    const localeFiles = [
      ...readLocaleFile('RefundPolicy.json'),
      ...readLocaleFile('footer.json'),
      ...readLocaleFile('delete-account.json'),
    ];

    for (const { locale, messages } of localeFiles) {
      const text = flattenMessages(messages).toLowerCase();

      for (const phrase of unsafePhrases) {
        expect(text, `${locale} contains unsafe phrase: ${phrase}`).not.toContain(phrase.toLowerCase());
      }
    }
  });
});
