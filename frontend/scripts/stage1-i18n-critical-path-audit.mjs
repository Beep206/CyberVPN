#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND_ROOT = path.resolve(SCRIPT_DIR, '..');
const CONFIG_PATH = path.join(FRONTEND_ROOT, 'src', 'i18n', 'config.ts');
const MESSAGES_ROOT = path.join(FRONTEND_ROOT, 'messages');
const CLIENT_NAMESPACES_PATH = path.join(FRONTEND_ROOT, 'src', 'i18n', 'client-namespaces.ts');
const MESSAGE_BUNDLE_GENERATOR_PATH = path.join(FRONTEND_ROOT, 'scripts', 'generate-message-bundles.mjs');
const GENERATED_MESSAGES_ROOT = path.join(FRONTEND_ROOT, 'src', 'i18n', 'messages', 'generated');

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
  'navigation.json',
  'servers.json',
  'subscriptions.json',
  'wallet.json',
  'payment-history.json',
  'settings.json',
  'devices.json',
  'messaging.json',
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

const DIRECT_REVIEWED_LOCALES = ['en-EN', 'ru-RU'];
const MIN_DIRECT_REVIEWED_COVERAGE = 0.85;
const S1_TOUCHED_MESSAGE_FILES = ['messaging.json', 'navigation.json'];
const S1_REQUIRED_DIRECT_REVIEWED_KEYS_BY_FILE = new Map([
  ['navigation.json', ['messages']],
]);
const HUMAN_READABLE_NAVIGATION_LOCALES = new Set(DIRECT_REVIEWED_LOCALES);
const UNCLEAR_PRIMARY_NAVIGATION_LABELS = new Set([
  'ALERTS',
  'CABINET',
  'CONFIG',
  'NETWORK',
  'КАБИНЕТ',
  'СЕТЬ',
]);
const RU_SAME_AS_ENGLISH_EXACT_ALLOWLIST = new Set([
  'API',
  'CyberVPN',
  'REST',
  'SSE',
  'Telegram',
  'Telegram Mini App',
  'URL',
  'VPN',
  'VLESS',
  'VLESS Reality RAW',
  'VLESS Reality XHTTP',
  'WireGuard',
  'iOS',
]);

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

function parseConstStringArray(source, exportName, sourcePath) {
  const match = source.match(
    new RegExp(`export const ${exportName}\\s*=\\s*\\[([\\s\\S]*?)\\]\\s*as const;`),
  );

  assert(match, `Could not find ${exportName} in ${path.relative(FRONTEND_ROOT, sourcePath)}`);

  return [...match[1].matchAll(/'([^']+)'/g)].map((item) => item[1]);
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

function sameStringEntries(left, right) {
  return (
    left.length === right.length &&
    left.every(
      ([key, value], index) => key === right[index][0] && value === right[index][1],
    )
  );
}

function containsUnsafePlaceholder(message) {
  return unsafePlaceholderPatterns.some((pattern) => pattern.test(message));
}

function normalizeNavigationLabel(label) {
  return label.trim().replace(/\s+/g, ' ').toLocaleUpperCase('ru-RU');
}

function formatCoverage(present, total) {
  return `${present}/${total} (${((present / total) * 100).toFixed(1)}%)`;
}

function formatKeyList(keys) {
  if (keys.length <= 8) {
    return keys.join(', ');
  }

  return `${keys.slice(0, 8).join(', ')}; ... ${keys.length - 8} more`;
}

function isAllowedRuSameAsEnglishValue(value) {
  const trimmedValue = value.trim();

  if (RU_SAME_AS_ENGLISH_EXACT_ALLOWLIST.has(trimmedValue)) {
    return true;
  }

  return /^[\d\s{}:/+_.@-]+$/.test(trimmedValue);
}

function assertMessagingBundleWiring(defaultLocale) {
  const clientNamespaceSource = readText(CLIENT_NAMESPACES_PATH);
  const dashboardClientNamespaces = parseConstStringArray(
    clientNamespaceSource,
    'DASHBOARD_CLIENT_NAMESPACES',
    CLIENT_NAMESPACES_PATH,
  );

  assert(
    dashboardClientNamespaces.includes('Messaging'),
    'DASHBOARD_CLIENT_NAMESPACES must include Messaging for dashboard client components',
  );

  const bundleGeneratorSource = readText(MESSAGE_BUNDLE_GENERATOR_PATH);
  assert(
    /['"]messaging\.json['"]\s*:\s*['"]Messaging['"]/.test(bundleGeneratorSource),
    'generate-message-bundles.mjs must map messaging.json to the Messaging namespace',
  );

  assertGeneratedNamespaceMatchesSource(defaultLocale, 'messaging.json', 'Messaging');
}

function assertGeneratedNamespaceMatchesSource(locale, fileName, namespace) {
  const sourceMessages = readLocaleFile(locale, fileName);
  assert(sourceMessages, `${locale}/${fileName} is required for ${namespace} bundle validation`);

  const generatedBundlePath = path.join(GENERATED_MESSAGES_ROOT, `${locale}.json`);
  const generatedBundle = readJson(generatedBundlePath);
  const generatedMessages = generatedBundle[namespace];

  assert(
    generatedMessages && typeof generatedMessages === 'object',
    `${path.relative(FRONTEND_ROOT, generatedBundlePath)} must include the ${namespace} namespace`,
  );

  const sourceEntries = [...toMessageMap(sourceMessages).entries()].sort(([left], [right]) =>
    left.localeCompare(right),
  );
  const generatedEntries = [...toMessageMap(generatedMessages).entries()].sort(([left], [right]) =>
    left.localeCompare(right),
  );

  assert(
    sameStringEntries(sourceEntries, generatedEntries),
    `${path.relative(FRONTEND_ROOT, generatedBundlePath)} ${namespace} namespace is stale or incomplete`,
  );
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
  assertMessagingBundleWiring(defaultLocale);

  for (const locale of DIRECT_REVIEWED_LOCALES) {
    assertGeneratedNamespaceMatchesSource(locale, 'messaging.json', 'Messaging');
    assertGeneratedNamespaceMatchesSource(locale, 'navigation.json', 'Navigation');
  }

  const localeGroups = Object.fromEntries(
    LOCALE_GROUPS.map((groupName) => [groupName, parseLocaleArray(configSource, groupName)]),
  );
  const locales = LOCALE_GROUPS.flatMap((groupName) => localeGroups[groupName]);
  const uniqueLocales = new Set(locales);
  const visibleFallbackLocales = locales.filter(
    (locale) => !DIRECT_REVIEWED_LOCALES.includes(locale),
  );

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
      const missingDirectKeys = [...defaultLeafMap.keys()].filter((key) => !localeLeafMap.has(key));

      if (
        DIRECT_REVIEWED_LOCALES.includes(locale) &&
        S1_TOUCHED_MESSAGE_FILES.includes(fileName) &&
        missingDirectKeys.length > 0
      ) {
        failures.push(
          `${locale}/${fileName}: direct reviewed touched namespace is missing ${missingDirectKeys.length} key(s): ${formatKeyList(
            missingDirectKeys,
          )}`,
        );
      }

      const requiredDirectReviewedKeys = S1_REQUIRED_DIRECT_REVIEWED_KEYS_BY_FILE.get(fileName) ?? [];
      for (const requiredKey of requiredDirectReviewedKeys) {
        if (DIRECT_REVIEWED_LOCALES.includes(locale) && !localeLeafMap.has(requiredKey)) {
          failures.push(`${locale}/${fileName}/${requiredKey}: required direct reviewed key is missing`);
        }
      }

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
          const localeValue = localeLeafMap.get(key);
          const defaultArgs = getIcuArgumentNames(defaultValue);
          const localeArgs = getIcuArgumentNames(localeValue);

          if (!sameStringArray(defaultArgs, localeArgs)) {
            failures.push(
              `${locale}/${fileName}/${key}: ICU argument mismatch; ${defaultLocale}={${defaultArgs.join(
                ', ',
              )}} locale={${localeArgs.join(', ')}}`,
            );
          }

          if (
            locale === 'ru-RU' &&
            S1_TOUCHED_MESSAGE_FILES.includes(fileName) &&
            localeValue === defaultValue &&
            !isAllowedRuSameAsEnglishValue(localeValue)
          ) {
            failures.push(`${locale}/${fileName}/${key}: suspicious same-as-English value "${localeValue}"`);
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
      DIRECT_REVIEWED_LOCALES.includes(locale) &&
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

    if (HUMAN_READABLE_NAVIGATION_LOCALES.has(locale)) {
      const navigationMessages = readLocaleFile(locale, 'navigation.json') ?? {};
      const navigationLeafMap = toMessageMap(navigationMessages);

      for (const [key, value] of navigationLeafMap) {
        const normalizedValue = normalizeNavigationLabel(value);

        if (UNCLEAR_PRIMARY_NAVIGATION_LABELS.has(normalizedValue)) {
          failures.push(
            `${locale}/navigation.json/${key}: unclear primary navigation label "${value}"`,
          );
        }
      }
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
  writeLine(`Touched namespace direct key parity: ${S1_TOUCHED_MESSAGE_FILES.join(', ')}`);
  writeLine('Messaging bundle wiring: dashboard client namespace + generated bundle path');
  writeLine(
    `Direct reviewed S1 locales: ${DIRECT_REVIEWED_LOCALES.join(', ')}; threshold >=${(
      MIN_DIRECT_REVIEWED_COVERAGE * 100
    ).toFixed(0)}%`,
  );
  writeLine(
    `Visible fallback locales: ${visibleFallbackLocales.length}; fallback incompleteness is a non-blocking warning when the ${defaultLocale} runtime merge remains complete.`,
  );

  writeLine('\nDirect source coverage by locale:');
  for (const row of directCoverageRows) {
    const missingSummary =
      row.missingFiles.length > 0 ? `; missing files: ${row.missingFiles.join(', ')}` : '';
    writeLine(`- ${row.locale}: ${formatCoverage(row.present, row.total)}${missingSummary}`);
  }

  const fallbackLocales = fallbackRows.filter(
    (row) => row.fallbackUsed > 0 && !DIRECT_REVIEWED_LOCALES.includes(row.locale),
  );
  writeLine(
    `\nNon-blocking fallback coverage warnings: ${fallbackLocales.length} visible locale(s) use at least one default ${defaultLocale} critical key.`,
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
  writeLine('PASS: direct reviewed touched namespaces have full key parity with en-EN.');
  writeLine('PASS: ru-RU touched namespace values are not suspicious same-as-English fallbacks.');
  writeLine('PASS: Messaging is wired into dashboard client namespaces and generated bundles.');
  writeLine('PASS: critical locale overrides keep ICU argument parity with the default locale.');
}

main();
