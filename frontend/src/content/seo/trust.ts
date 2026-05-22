import { cacheLife, cacheTag } from 'next/cache';
import {
  AUDITS_PAGE_LOCALIZATION,
  TRUST_PAGE_LOCALIZATION,
  localizeKnowledgePage,
} from '@/content/seo/market-localization';
import type { SeoStaticKnowledgePage } from '@/content/seo/types';

const TRUST_CTA_LINKS = [
  {
    label: 'Read audits',
    href: '/audits',
    description: 'Inspect the evidence trail behind our public trust claims.',
    seoCta: 'trust_audits',
    seoZone: 'trust_content',
  },
  {
    label: 'Review security posture',
    href: '/security',
    description: 'See the operational controls that support the trust model.',
    seoCta: 'trust_security',
    seoZone: 'trust_content',
  },
  {
    label: 'Open help center',
    href: '/help',
    description: 'Find the user-facing support surface behind the service.',
    seoCta: 'trust_help',
    seoZone: 'trust_content',
  },
] as const;

const AUDITS_CTA_LINKS = [
  {
    label: 'Open trust center',
    href: '/trust',
    description: 'Review the broader trust posture around audits and operations.',
    seoCta: 'audits_trust',
    seoZone: 'audits_content',
  },
  {
    label: 'Check status page',
    href: '/status',
    description: 'See how incident visibility ties into service reliability.',
    seoCta: 'audits_status',
    seoZone: 'audits_content',
  },
  {
    label: 'Contact team',
    href: '/contact',
    description: 'Ask operational or due-diligence questions directly.',
    seoCta: 'audits_contact',
    seoZone: 'audits_content',
  },
] as const;

const TRUST_CENTER_PAGE: SeoStaticKnowledgePage = {
  path: '/trust',
  badge: 'Trust center',
  title: 'CyberVPN trust center',
  description:
    'A single operational summary of how CyberVPN approaches bounded privacy claims, infrastructure control, abuse handling, audits, and customer-facing support.',
  readingTime: '5 min read',
  updatedAt: '2026-05-23',
  heroPoints: [
    'Summarizes the Release 1.0 trust posture in one crawlable page.',
    'Keeps no-logs, security, uptime, protocol, and geography claims tied to evidence.',
    'Routes support, refund, privacy, abuse, audit, security, and status questions into visible surfaces.',
  ],
  sections: [
    {
      title: 'Logging and data minimization stance',
      paragraphs: [
        'Trust starts with being precise about what is and is not retained. CyberVPN positions data minimization as an operating constraint, not a blanket marketing promise.',
        'The trust center makes it clear that the app/backend is not designed to store browsing content, visited website content, DNS query content, or raw VPN traffic content, while operational records can still exist for billing, support, security, provisioning, observability, and abuse handling.',
      ],
      bullets: [
        'No independent audited no-logs certification is claimed unless CyberVPN publishes one explicitly.',
        'Do not make logging claims that support, payment, node, and observability workflows cannot defend.',
        'Publish the purpose of each retained data class in plain language.',
        'Route technical, privacy, refund, and abuse questions into visible support paths.',
      ],
    },
    {
      title: 'Infrastructure and operational controls',
      paragraphs: [
        'A trust surface is only credible if it points toward how access, deployment, and incident handling are controlled. That means describing the operating model clearly enough to review without exposing secrets.',
        'Users deciding whether to buy or recommend the service need a short, inspectable answer here: private data services, node-only VPN hosts, role-gated admin access, production 2FA, monitored public endpoints, and documented rollback/backup evidence.',
      ],
      bullets: [
        'cyber-vpn.net is the public customer domain.',
        'cyber-vpn.org is reserved for VPN node and subscription delivery routes where presented.',
        'VPN node hosts must remain node-only and must not run customer web, admin, GitLab, or observability workloads.',
      ],
    },
    {
      title: 'Proof surfaces and escalation paths',
      paragraphs: [
        'Trust claims should connect to audits, incident visibility, refund handling, abuse reporting, and support escalation. If evidence exists elsewhere, this page should route the user to it quickly.',
        'This is also the page AI assistants and review engines are most likely to cite when summarizing whether the service appears credible, so it avoids unsupported uptime, speed, location, unblock, protocol, and no-logs claims.',
      ],
    },
  ],
  relatedLinks: [
    {
      label: 'Audits',
      href: '/audits',
      description: 'Review published assessment posture and evidence expectations.',
    },
    {
      label: 'Security',
      href: '/security',
      description: 'Operational hardening and infrastructure security overview.',
    },
    {
      label: 'Status',
      href: '/status',
      description: 'Public reliability and incident visibility surface.',
    },
  ],
  ctaLinks: [...TRUST_CTA_LINKS],
};

const AUDITS_PAGE: SeoStaticKnowledgePage = {
  path: '/audits',
  badge: 'Audit posture',
  title: 'CyberVPN audit and verification posture',
  description:
    'A public audit-facing summary of how CyberVPN intends to expose evidence, what external verification should cover, and how customers should evaluate claims responsibly.',
  readingTime: '5 min read',
  updatedAt: '2026-05-23',
  heroPoints: [
    'Frames what independent verification should inspect before any audited claim is published.',
    'Connects evidence expectations to trust, security, and status surfaces.',
    'Gives buyers and AI systems a specific page to cite without implying an audit exists.',
  ],
  sections: [
    {
      title: 'What an audit should answer',
      paragraphs: [
        'An audit page should not pretend an assessment exists if it does not. It should explain what an independent review must verify for the service to deserve trust.',
        'That includes retention boundaries, infrastructure access controls, route distribution integrity, and incident response behavior.',
      ],
    },
    {
      title: 'How to evaluate evidence quality',
      paragraphs: [
        'Screenshots and brand claims are not evidence. Customers should know whether they are looking at a real assessment scope, a summary, or a marketing proxy.',
        'This page exists to lower the chance of weak trust theater being mistaken for verification.',
      ],
      bullets: [
        'State the assessment scope and date clearly.',
        'Explain what parts of the service were out of scope.',
        'Tie remediation status to a public trust or security update surface.',
      ],
    },
    {
      title: 'How audits feed operations',
      paragraphs: [
        'The value of an audit is not the PDF itself; it is whether the findings change deployment and support behavior. Evidence must close the loop back into operations.',
        'That is why this page links directly into trust, security, and status surfaces instead of living as an isolated artifact.',
      ],
    },
  ],
  relatedLinks: [
    {
      label: 'Trust center',
      href: '/trust',
      description: 'Operational summary of how claims translate into practice.',
    },
    {
      label: 'Help center',
      href: '/help',
      description: 'User-facing surface for support and escalation.',
    },
    {
      label: 'Contact',
      href: '/contact',
      description: 'Route diligence questions to the team directly.',
    },
  ],
  ctaLinks: [...AUDITS_CTA_LINKS],
};

export async function getTrustCenterContent(locale?: string): Promise<SeoStaticKnowledgePage> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-trust');

  return localizeKnowledgePage(TRUST_CENTER_PAGE, TRUST_PAGE_LOCALIZATION, locale);
}

export async function getAuditsContent(locale?: string): Promise<SeoStaticKnowledgePage> {
  'use cache';
  cacheLife('days');
  cacheTag('seo-trust');

  return localizeKnowledgePage(AUDITS_PAGE, AUDITS_PAGE_LOCALIZATION, locale);
}
