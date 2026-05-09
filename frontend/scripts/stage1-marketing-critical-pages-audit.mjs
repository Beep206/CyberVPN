#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND_ROOT = path.resolve(SCRIPT_DIR, '..');
const EXPECTED_SITE_URL = 'https://cyber-vpn.net';

const CRITICAL_ROUTE_FILES = [
  'src/app/[locale]/(marketing)/page.tsx',
  'src/app/[locale]/(marketing)/pricing/page.tsx',
  'src/app/[locale]/(marketing)/features/page.tsx',
  'src/app/[locale]/(marketing)/devices/page.tsx',
  'src/app/[locale]/(marketing)/devices/[slug]/page.tsx',
  'src/app/[locale]/(marketing)/help/page.tsx',
  'src/app/[locale]/(marketing)/status/page.tsx',
  'src/app/[locale]/(marketing)/terms/page.tsx',
  'src/app/[locale]/(marketing)/privacy/page.tsx',
  'src/app/[locale]/(marketing)/privacy-policy/page.tsx',
  'src/app/[locale]/(marketing)/acceptable-use/page.tsx',
  'src/app/[locale]/(marketing)/refund-policy/page.tsx',
  'src/app/[locale]/(marketing)/cookie-policy/page.tsx',
];

const CRITICAL_MESSAGE_FILES = [
  'messages/en-EN/landing.json',
  'messages/ru-RU/landing.json',
  'messages/en-EN/Pricing.json',
  'messages/ru-RU/Pricing.json',
  'messages/en-EN/Features.json',
  'messages/ru-RU/Features.json',
  'messages/en-EN/HelpCenter.json',
  'messages/ru-RU/HelpCenter.json',
  'messages/en-EN/Status.json',
  'messages/ru-RU/Status.json',
  'messages/en-EN/Terms.json',
  'messages/ru-RU/Terms.json',
  'messages/en-EN/Privacy.json',
  'messages/ru-RU/Privacy.json',
  'messages/en-EN/AcceptableUse.json',
  'messages/ru-RU/AcceptableUse.json',
  'messages/en-EN/RefundPolicy.json',
  'messages/ru-RU/RefundPolicy.json',
  'messages/en-EN/CookiePolicy.json',
  'messages/ru-RU/CookiePolicy.json',
];

const MARKETING_COPY_FILES = [
  'messages/en-EN/landing.json',
  'messages/ru-RU/landing.json',
  'messages/en-EN/Pricing.json',
  'messages/ru-RU/Pricing.json',
  'messages/en-EN/Features.json',
  'messages/ru-RU/Features.json',
  'messages/en-EN/HelpCenter.json',
  'messages/ru-RU/HelpCenter.json',
  'messages/en-EN/Status.json',
  'messages/ru-RU/Status.json',
];

const REQUIRED_LEGAL_ROUTE_FILES = [
  'src/app/[locale]/(marketing)/terms/page.tsx',
  'src/app/[locale]/(marketing)/privacy/page.tsx',
  'src/app/[locale]/(marketing)/acceptable-use/page.tsx',
  'src/app/[locale]/(marketing)/refund-policy/page.tsx',
  'src/app/[locale]/(marketing)/cookie-policy/page.tsx',
];

const placeholderPatterns = [
  /\bTODO\b/,
  /\bFIXME\b/,
  /\bTBD\b/,
  /\bREPLACE_ME\b/i,
  /lorem ipsum/i,
  /vpn\.ozoxy\.ru/i,
  /get\.cybervpn\.com/i,
];

const unsupportedMarketingClaimPatterns = [
  /99\.9/i,
  /99\.99/i,
  /100\+\s*(active\s*)?(nodes|locations)/i,
  /50\+\s*(countries|стран)/i,
  /10\s*gbit/i,
  /10gbps/i,
  /zero\s*limits/i,
  /no\s*disks/i,
  /no\s*logs/i,
  /zero[-\s]?logs/i,
  /strict\s+no[-\s]?logs/i,
  /zero[-\s]?knowledge/i,
  /military[-\s]?grade/i,
  /quantum/i,
  /post[-\s]?quantum/i,
  /multi[-\s]?hop/i,
  /kill\s*switch/i,
  /anonymous payments/i,
  /monero/i,
  /untraceable/i,
  /p2p optimized/i,
  /torrenting/i,
  /dedicated high-bandwidth nodes/i,
  /any complexity/i,
  /guarantee/i,
  /guaranteed/i,
  /automatically masks/i,
  /indistinguishable/i,
  /auto-renew/i,
  /autorenew/i,
  /renews automatically/i,
  /recurring billing/i,
];

function writeLine(message = '') {
  process.stdout.write(`${message}\n`);
}

function readText(relativePath) {
  return fs.readFileSync(path.join(FRONTEND_ROOT, relativePath), 'utf8');
}

function readJson(relativePath) {
  return JSON.parse(readText(relativePath));
}

function flattenStrings(value, prefix = '') {
  if (typeof value === 'string') {
    return [[prefix, value]];
  }

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return [];
  }

  return Object.entries(value).flatMap(([key, child]) =>
    flattenStrings(child, prefix ? `${prefix}.${key}` : key),
  );
}

function findPatternMatches(text, patterns) {
  return patterns.filter((pattern) => pattern.test(text)).map((pattern) => pattern.source);
}

function main() {
  const failures = [];

  for (const relativePath of CRITICAL_ROUTE_FILES) {
    if (!fs.existsSync(path.join(FRONTEND_ROOT, relativePath))) {
      failures.push(`${relativePath}: missing critical marketing route file`);
    }
  }

  for (const relativePath of CRITICAL_MESSAGE_FILES) {
    if (!fs.existsSync(path.join(FRONTEND_ROOT, relativePath))) {
      failures.push(`${relativePath}: missing critical message file`);
    }
  }

  const seoRoutePolicy = readText('src/shared/lib/seo-route-policy.ts');
  if (!seoRoutePolicy.includes(`SITE_URL = '${EXPECTED_SITE_URL}'`)) {
    failures.push(`src/shared/lib/seo-route-policy.ts: SITE_URL must be ${EXPECTED_SITE_URL}`);
  }

  for (const relativePath of [...CRITICAL_MESSAGE_FILES, ...CRITICAL_ROUTE_FILES]) {
    const text = readText(relativePath);
    const matches = findPatternMatches(text, placeholderPatterns);

    if (matches.length > 0) {
      failures.push(`${relativePath}: placeholder or stale-domain pattern found: ${matches.join(', ')}`);
    }
  }

  for (const relativePath of MARKETING_COPY_FILES) {
    const messages = readJson(relativePath);

    for (const [key, value] of flattenStrings(messages)) {
      const matches = findPatternMatches(value, unsupportedMarketingClaimPatterns);

      if (matches.length > 0) {
        failures.push(`${relativePath}:${key}: unsupported S1 marketing claim: ${matches.join(', ')}`);
      }
    }
  }

  for (const relativePath of REQUIRED_LEGAL_ROUTE_FILES) {
    const text = readText(relativePath);
    if (!text.includes('withSiteMetadata')) {
      failures.push(`${relativePath}: legal route must use site metadata policy`);
    }
  }

  writeLine('S1 marketing critical pages audit');
  writeLine(`Critical route files: ${CRITICAL_ROUTE_FILES.length}`);
  writeLine(`Critical message files: ${CRITICAL_MESSAGE_FILES.length}`);
  writeLine(`Canonical site URL: ${EXPECTED_SITE_URL}`);
  writeLine(`Marketing copy files scanned for unsupported claims: ${MARKETING_COPY_FILES.length}`);

  if (failures.length > 0) {
    process.stderr.write('\nS1 marketing audit failures:\n');
    for (const failure of failures) {
      process.stderr.write(`- ${failure}\n`);
    }
    process.exit(1);
  }

  writeLine('\nPASS: critical marketing route files exist.');
  writeLine('PASS: critical EN/RU marketing and legal message files exist.');
  writeLine('PASS: canonical public URL is cyber-vpn.net.');
  writeLine('PASS: no placeholder, stale-domain, or unsupported S1 marketing-claim patterns found.');
}

main();
