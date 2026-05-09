import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import enTerms from '../../../../messages/en-EN/Terms.json';
import ruTerms from '../../../../messages/ru-RU/Terms.json';

type TermsMessages = typeof enTerms;

const unsafePhrases = [
  '99.9',
  'neural networks',
  'cybernetic contract',
  'hardware layer',
  'without explanation',
  'unconditional acceptance',
  'renews automatically',
];

function flattenTerms(messages: TermsMessages): string {
  return [
    messages.title,
    messages.description,
    ...Object.values(messages.sections).flatMap((section) => [
      section.title,
      section.content,
      ...Object.values('rules' in section ? section.rules : {}),
    ]),
    messages.terminal.prompt,
    messages.terminal.command,
    messages.terminal.verified,
  ].join('\n');
}

function readAllTermsMessages(): Array<{ locale: string; messages: TermsMessages }> {
  const messagesRoot = join(process.cwd(), 'messages');

  return readdirSync(messagesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const filePath = join(messagesRoot, entry.name, 'Terms.json');
      const messages = JSON.parse(readFileSync(filePath, 'utf8')) as TermsMessages;

      return { locale: entry.name, messages };
    });
}

describe('S1 Terms of Service copy', () => {
  it('keeps EN/RU public terms aligned with S1 legal decisions and support contacts', () => {
    for (const messages of [enTerms, ruTerms]) {
      const body = flattenTerms(messages).toLowerCase();

      expect(body).toContain('individual founder/owner');
      expect(body).toMatch(/jurisdiction|юрисдик/);
      expect(body).toContain('support@cyber-vpn.net');
      expect(body).toContain('refund@cyber-vpn.net');
      expect(body).toContain('controlled public beta');
      expect(body).toContain('remnawave');
      expect(body).toContain('2fa');
      expect(body).toContain('cvv');
      expect(body).toContain('raw subscription');
    }
  });

  it('removes launch-unsafe fantasy, uptime and autoprolongation language', () => {
    for (const { messages } of readAllTermsMessages()) {
      const body = flattenTerms(messages).toLowerCase();

      for (const phrase of unsafePhrases) {
        expect(body).not.toContain(phrase);
      }
    }
  });

  it('covers S1 abuse categories required before a public beta terms page', () => {
    const rules = enTerms.sections.prohibited.rules;

    expect(Object.values(rules).join('\n').toLowerCase()).toContain('credential stuffing');
    expect(Object.values(rules).join('\n').toLowerCase()).toContain('malware');
    expect(Object.values(rules).join('\n').toLowerCase()).toContain('minors');
    expect(Object.values(rules).join('\n').toLowerCase()).toContain('sanctions');
  });
});
