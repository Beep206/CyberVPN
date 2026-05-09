#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND_ROOT = path.resolve(SCRIPT_DIR, '..');
const CONFIG_PATH = path.join(FRONTEND_ROOT, 'src', 'i18n', 'config.ts');
const MESSAGES_ROOT = path.join(FRONTEND_ROOT, 'messages');

const LOCALE_GROUPS = [
  'highPriorityLocales',
  'mediumPriorityLocales',
  'lowPriorityLocales',
  'requiredFallbackLocales',
  'additionalLocales',
];

const S1_CRITICAL_MESSAGE_FILES = [
  'auth.json',
  'dashboard.json',
  'servers.json',
  'subscriptions.json',
  'wallet.json',
  'payment-history.json',
  'settings.json',
  'devices.json',
  'MiniApp.json',
  'Pricing.json',
  'HelpCenter.json',
  'Status.json',
  'Download.json',
  'Terms.json',
  'Privacy.json',
  'AcceptableUse.json',
  'RefundPolicy.json',
  'CookiePolicy.json',
];

const S1_DIRECT_REVIEWED_LOCALES = ['en-EN', 'ru-RU'];
const MIN_DIRECT_REVIEWED_COVERAGE = 0.85;

const unsafePlaceholderPatterns = [
  /\bTODO\b/,
  /\bFIXME\b/,
  /\bTBD\b/,
  /\bREPLACE_ME\b/i,
  /lorem ipsum/i,
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function readJson(filePath) {
  return JSON.parse(readText(filePath));
}

function parseLocaleArray(configSource, exportName) {
  const match = configSource.match(
    new RegExp(`export const ${exportName}\\s*=\\s*\\[([\\s\\S]*?)\\]\\s*as const;`),
  );

  assert(match, `Could not find ${exportName} in ${path.relative(FRONTEND_ROOT, CONFIG_PATH)}`);

  return [...match[1].matchAll(/'([^']+)'/g)].map((item) => item[1]);
}

function parseDefaultLocale(configSource) {
  const match = configSource.match(/export const defaultLocale\s*=\s*'([^']+)';/);

  assert(match, `Could not find defaultLocale in ${path.relative(FRONTEND_ROOT, CONFIG_PATH)}`);

  return match[1];
}

function readLocaleFile(locale, fileName) {
  const filePath = path.join(MESSAGES_ROOT, locale, fileName);

  if (!fs.existsSync(filePath)) {
    return null;
  }

  return readJson(filePath);
}

function deepMergeFallback(base, override) {
  if (override === undefined || override === null) {
    return base;
  }

  if (
    base &&
    override &&
    typeof base === 'object' &&
    typeof override === 'object' &&
    !Array.isArray(base) &&
    !Array.isArray(override)
  ) {
    const merged = { ...base };

    for (const [key, value] of Object.entries(override)) {
      merged[key] = deepMergeFallback(base[key], value);
    }

    return merged;
  }

  return override;
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

function toMessageMap(messages) {
  return new Map(flattenStrings(messages));
}

function getIcuArgumentNames(message) {
  const names = new Set();
  const regex = /\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:[,}])/g;
  let match;

  while ((match = regex.exec(message)) !== null) {
    names.add(match[1]);
  }

  return [...names].sort();
}

function sameStringArray(left, right) {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function containsUnsafePlaceholder(message) {
  return unsafePlaceholderPatterns.some((pattern) => pattern.test(message));
}

function formatCoverage(present, total) {
  return `${present}/${total} (${((present / total) * 100).toFixed(1)}%)`;
}

function writeLine(message = '') {
  process.stdout.write(`${message}\n`);
}

function writeErrorLine(message = '') {
  process.stderr.write(`${message}\n`);
}

function main() {
  const configSource = readText(CONFIG_PATH);
  const defaultLocale = parseDefaultLocale(configSource);
  const localeGroups = Object.fromEntries(
    LOCALE_GROUPS.map((groupName) => [groupName, parseLocaleArray(configSource, groupName)]),
  );
  const locales = LOCALE_GROUPS.flatMap((groupName) => localeGroups[groupName]);
  const uniqueLocales = new Set(locales);

  assert(
    uniqueLocales.size === locales.length,
    `Duplicate locales detected: ${locales.filter((locale, index) => locales.indexOf(locale) !== index).join(', ')}`,
  );
  assert(locales.includes(defaultLocale), `defaultLocale ${defaultLocale} is not in locales`);

  const defaultMessagesByFile = new Map();
  const defaultLeafMapsByFile = new Map();
  let defaultLeafTotal = 0;

  for (const fileName of S1_CRITICAL_MESSAGE_FILES) {
    const messages = readLocaleFile(defaultLocale, fileName);

    assert(messages, `${defaultLocale}/${fileName} is required for S1 i18n fallback`);

    const leafMap = toMessageMap(messages);

    assert(leafMap.size > 0, `${defaultLocale}/${fileName} has no string messages`);

    defaultMessagesByFile.set(fileName, messages);
    defaultLeafMapsByFile.set(fileName, leafMap);
    defaultLeafTotal += leafMap.size;
  }

  const failures = [];
  const directCoverageRows = [];
  const fallbackRows = [];
  let runtimeMessageCount = 0;
  let directReviewedCoveragePass = true;

  for (const locale of locales) {
    let directPresent = 0;
    let fallbackUsed = 0;
    let directTotal = 0;
    const missingFiles = [];

    for (const fileName of S1_CRITICAL_MESSAGE_FILES) {
      const defaultMessages = defaultMessagesByFile.get(fileName);
      const defaultLeafMap = defaultLeafMapsByFile.get(fileName);
      const localeMessages = readLocaleFile(locale, fileName);
      const localeLeafMap = toMessageMap(localeMessages ?? {});

      if (!localeMessages) {
        missingFiles.push(fileName);
      }

      directTotal += defaultLeafMap.size;
      directPresent += [...defaultLeafMap.keys()].filter((key) => localeLeafMap.has(key)).length;

      const mergedMessages = deepMergeFallback(defaultMessages, localeMessages ?? {});
      const mergedLeafMap = toMessageMap(mergedMessages);

      for (const [key, defaultValue] of defaultLeafMap) {
        const mergedValue = mergedLeafMap.get(key);

        if (typeof mergedValue !== 'string') {
          failures.push(`${locale}/${fileName}/${key}: missing after ${defaultLocale} fallback merge`);
          continue;
        }

        runtimeMessageCount += 1;

        if (!localeLeafMap.has(key)) {
          fallbackUsed += 1;
        }

        if (containsUnsafePlaceholder(mergedValue)) {
          failures.push(`${locale}/${fileName}/${key}: unsafe placeholder text detected`);
        }

        if (localeLeafMap.has(key)) {
          const defaultArgs = getIcuArgumentNames(defaultValue);
          const localeArgs = getIcuArgumentNames(localeLeafMap.get(key));

          if (!sameStringArray(defaultArgs, localeArgs)) {
            failures.push(
              `${locale}/${fileName}/${key}: ICU argument mismatch; ${defaultLocale}={${defaultArgs.join(
                ', ',
              )}} locale={${localeArgs.join(', ')}}`,
            );
          }
        }
      }
    }

    const coverage = directPresent / directTotal;

    directCoverageRows.push({
      locale,
      coverage,
      missingFiles,
      present: directPresent,
      total: directTotal,
    });
    fallbackRows.push({ locale, fallbackUsed });

    if (
      S1_DIRECT_REVIEWED_LOCALES.includes(locale) &&
      (missingFiles.length > 0 || coverage < MIN_DIRECT_REVIEWED_COVERAGE)
    ) {
      directReviewedCoveragePass = false;
      failures.push(
        `${locale}: direct reviewed coverage ${formatCoverage(
          directPresent,
          directTotal,
        )} is below ${(MIN_DIRECT_REVIEWED_COVERAGE * 100).toFixed(0)}% or has missing critical files`,
      );
    }
  }

  directCoverageRows.sort((left, right) => left.locale.localeCompare(right.locale));
  fallbackRows.sort((left, right) => right.fallbackUsed - left.fallbackUsed);

  writeLine('S1 i18n critical-path audit');
  writeLine(`Enabled locales: ${locales.length}`);
  writeLine(`Default fallback locale: ${defaultLocale}`);
  writeLine(`Critical message files: ${S1_CRITICAL_MESSAGE_FILES.length}`);
  writeLine(`Default critical string keys: ${defaultLeafTotal}`);
  writeLine(`Runtime fallback-merged checks: ${runtimeMessageCount}`);
  writeLine(
    `Direct reviewed S1 locales: ${S1_DIRECT_REVIEWED_LOCALES.join(', ')}; threshold >=${(
      MIN_DIRECT_REVIEWED_COVERAGE * 100
    ).toFixed(0)}%`,
  );

  writeLine('\nDirect source coverage by locale:');
  for (const row of directCoverageRows) {
    const missingSummary =
      row.missingFiles.length > 0 ? `; missing files: ${row.missingFiles.join(', ')}` : '';
    writeLine(`- ${row.locale}: ${formatCoverage(row.present, row.total)}${missingSummary}`);
  }

  const fallbackLocales = fallbackRows.filter((row) => row.fallbackUsed > 0);
  writeLine(
    `\nFallback-supported locales with at least one default ${defaultLocale} critical key: ${fallbackLocales.length}`,
  );
  writeLine(
    fallbackLocales
      .slice(0, 12)
      .map((row) => `- ${row.locale}: ${row.fallbackUsed} fallback keys`)
      .join('\n'),
  );

  if (fallbackLocales.length > 12) {
    writeLine(`- ... ${fallbackLocales.length - 12} more locale(s) use fallback for critical keys`);
  }

  if (failures.length > 0) {
    writeErrorLine('\nS1 i18n audit failures:');
    for (const failure of failures) {
      writeErrorLine(`- ${failure}`);
    }
    process.exit(1);
  }

  assert(directReviewedCoveragePass, 'Direct reviewed S1 locale coverage gate failed');

  writeLine('\nPASS: all enabled locales are runtime fallback-complete for S1 critical paths.');
  writeLine('PASS: direct reviewed S1 locales meet the local launch coverage threshold.');
  writeLine('PASS: critical locale overrides keep ICU argument parity with the default locale.');
}

main();
