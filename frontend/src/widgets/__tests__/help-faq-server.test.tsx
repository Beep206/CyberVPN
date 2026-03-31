import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { HelpCategories } from '../help-categories';
import { HelpFaq } from '../help-faq';

const messages = {
  categories_title: 'KNOWLEDGE MODULES',
  categories_intro:
    'Pick a verified module and jump straight to the relevant answers.',
  faq_title: 'COMMON QUERIES',
  faq_intro:
    'Browse initialization, routing, billing, and security answers without waiting for hydration.',
  category_getting_started: 'Initialization',
  category_getting_started_desc: 'System startup and basic configuration protocols.',
  category_troubleshooting: 'Signal Routing',
  category_troubleshooting_desc: 'Diagnostics for connection and tunneling errors.',
  category_billing: 'Access Credits',
  category_billing_desc: 'Subscription, payments, and bandwidth allocation.',
  category_security: 'Encryption Protocols',
  category_security_desc: 'Details on Anti-DPI, obfuscation, and zero-logs policies.',
  faq_getting_started_1_q: 'How do I initialize my first connection?',
  faq_getting_started_1_a:
    "Download the core module, authenticate, and click 'Engage'.",
  faq_getting_started_2_q: 'What devices are supported?',
  faq_getting_started_2_a: 'Windows, macOS, Linux, iOS, and Android are supported.',
  faq_getting_started_3_q: 'Can I connect multiple devices simultaneously?',
  faq_getting_started_3_a: 'Yes, depending on your plan you can connect multiple devices.',
  faq_troubleshooting_1_q: 'Why is my connection speed degraded?',
  faq_troubleshooting_1_a: 'Check ping and reroute to an alternate shard.',
  faq_troubleshooting_2_q: 'What if the primary proxy fails?',
  faq_troubleshooting_2_a: 'Fallback routing engages automatically.',
  faq_troubleshooting_3_q: 'How do I bypass DPI restrictions?',
  faq_troubleshooting_3_a: 'Use the latest VLESS+Reality-capable core.',
  faq_billing_1_q: 'How do I increase my bandwidth quota?',
  faq_billing_1_a: 'Acquire additional credits in the billing terminal.',
  faq_billing_2_q: 'Are refunds available for inactive cycles?',
  faq_billing_2_a: 'Refunds are limited to the initial 72-hour window.',
  faq_billing_3_q: 'Do you support anonymous payments?',
  faq_billing_3_a: 'Yes, crypto payments are supported.',
  faq_security_1_q: 'Is my data logged?',
  faq_security_1_a: 'No, the service follows a zero-knowledge architecture.',
  faq_security_2_q: 'What encryption standard is deployed?',
  faq_security_2_a: 'ChaCha20-Poly1305 and AES-256-GCM are supported.',
  faq_security_3_q: 'Do you offer a Kill Switch?',
  faq_security_3_a: 'Yes, the client can cut network access on tunnel failure.',
} as const;

vi.mock('next-intl/server', () => ({
  getTranslations: vi.fn(async () => (key: keyof typeof messages) => messages[key] ?? key),
}));

vi.mock('../help-faq-client', () => ({
  HelpFaqClient: () => null,
}));

describe('Help Center server knowledge surface', () => {
  it('renders server-side category anchors for knowledge navigation', async () => {
    render(await HelpCategories());

    expect(
      screen.getByRole('link', { name: /Initialization/i }),
    ).toHaveAttribute('href', '?category=getting_started#faq-getting_started');
    expect(screen.getByText(messages.categories_intro)).toBeInTheDocument();
  });

  it('renders FAQ questions and answers in the HTML baseline', async () => {
    render(await HelpFaq());

    expect(
      screen.getByRole('heading', {
        name: 'How do I initialize my first connection?',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Download the core module, authenticate, and click 'Engage'."),
    ).toBeInTheDocument();
    expect(screen.getByText(messages.faq_intro)).toBeInTheDocument();
  });
});
