import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  buildLocaleBundle,
  MESSAGE_FILE_NAMESPACE_MAP,
  MESSAGES_ROOT,
  OUTPUT_ROOT,
  PROJECT_ROOT,
} from './generate-message-bundles.mjs';

const DIRECT_REVIEW_LOCALES = ['en-EN', 'ru-RU'];
const CRITICAL_MESSAGE_FILES = [
  'navigation.json',
  'dashboard.json',
  'sections.json',
  'growth.json',
  'customers.json',
  'language-selector.json',
];

const RU_FORBIDDEN_TERMS = [
  'cockpit',
  'Permissions',
  'Sensitive action',
  'Read surface',
  'Operator action',
  'support tickets',
  'Risk reviews',
  'Growth abuse signals',
  'callback errors',
  'Pricebooks',
  'Realtime',
  'Governance',
  'Review queue',
  'Risk signals',
  'Webhook log',
  'Admin invites',
];

const RU_GLOSSARY_EXPECTATIONS = [
  ['navigation.json', 'integrationsHint', 'Telegram, push, реалтайм'],
  ['governance.json', 'nav.webhookLog', 'Журнал вебхуков'],
  ['governance.json', 'nav.adminInvites', 'Инвайты админов'],
  ['integrations.json', 'nav.realtime', 'Реалтайм'],
  ['security-admin.json', 'reviewQueue.title', 'Очередь проверок'],
];

const findings = [];

function addFinding(severity, code, message) {
  findings.push({ severity, code, message });
}

function isJsonObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function collectLeafPaths(value, prefix = '') {
  if (!isJsonObject(value)) {
    return [prefix];
  }

  return Object.entries(value).flatMap(([key, nestedValue]) =>
    collectLeafPaths(nestedValue, prefix ? `${prefix}.${key}` : key),
  );
}

function collectStringValues(value, prefix = '') {
  if (typeof value === 'string') {
    return [[prefix, value]];
  }

  if (Array.isArray(value)) {
    return value.flatMap((item, index) => collectStringValues(item, `${prefix}[${index}]`));
  }

  if (!isJsonObject(value)) {
    return [];
  }

  return Object.entries(value).flatMap(([key, nestedValue]) =>
    collectStringValues(nestedValue, prefix ? `${prefix}.${key}` : key),
  );
}

function getValueAtPath(value, dottedPath) {
  return dottedPath.split('.').reduce((current, key) => {
    if (!isJsonObject(current)) {
      return undefined;
    }

    return current[key];
  }, value);
}

function stableStringify(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function readJsonFile(filePath) {
  const raw = await readFile(filePath, 'utf8');
  return JSON.parse(raw);
}

async function auditCriticalCoverage() {
  for (const fileName of CRITICAL_MESSAGE_FILES) {
    const localeMessages = new Map();

    for (const locale of DIRECT_REVIEW_LOCALES) {
      const filePath = path.join(MESSAGES_ROOT, locale, fileName);

      try {
        localeMessages.set(locale, await readJsonFile(filePath));
      } catch (error) {
        addFinding(
          'P0',
          'missing_or_invalid_critical_file',
          `${locale}/${fileName}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }

    if (localeMessages.size !== DIRECT_REVIEW_LOCALES.length) {
      continue;
    }

    const [referenceLocale, targetLocale] = DIRECT_REVIEW_LOCALES;
    const referenceKeys = new Set(collectLeafPaths(localeMessages.get(referenceLocale)));
    const targetKeys = new Set(collectLeafPaths(localeMessages.get(targetLocale)));

    for (const key of referenceKeys) {
      if (!targetKeys.has(key)) {
        addFinding('P0', 'missing_ru_key', `${targetLocale}/${fileName} is missing ${key}`);
      }
    }

    for (const key of targetKeys) {
      if (!referenceKeys.has(key)) {
        addFinding('P1', 'extra_ru_key', `${targetLocale}/${fileName} has extra ${key}`);
      }
    }
  }
}

async function auditRussianGlossary() {
  const ruDir = path.join(MESSAGES_ROOT, 'ru-RU');
  const ruFiles = (await readdir(ruDir)).filter((fileName) => fileName.endsWith('.json')).sort();
  const forbiddenPatterns = RU_FORBIDDEN_TERMS.map((term) => [term, new RegExp(escapeRegExp(term), 'iu')]);

  for (const fileName of ruFiles) {
    const messages = await readJsonFile(path.join(ruDir, fileName));

    for (const [messagePath, value] of collectStringValues(messages)) {
      for (const [term, pattern] of forbiddenPatterns) {
        if (pattern.test(value)) {
          addFinding('P1', 'ru_glossary_mixing', `ru-RU/${fileName}:${messagePath} contains "${term}"`);
        }
      }
    }
  }

  for (const [fileName, messagePath, expected] of RU_GLOSSARY_EXPECTATIONS) {
    const messages = await readJsonFile(path.join(ruDir, fileName));
    const actual = getValueAtPath(messages, messagePath);

    if (actual !== expected) {
      addFinding(
        'P1',
        'ru_glossary_expected_term',
        `ru-RU/${fileName}:${messagePath} expected "${expected}", got "${String(actual)}"`,
      );
    }
  }
}

async function auditGeneratedBundlesFreshness() {
  const localeDirs = (await readdir(MESSAGES_ROOT, { withFileTypes: true }))
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right));

  for (const locale of localeDirs) {
    const expected = stableStringify(await buildLocaleBundle(locale));
    const generatedPath = path.join(OUTPUT_ROOT, `${locale}.json`);

    let actual;
    try {
      actual = await readFile(generatedPath, 'utf8');
    } catch (error) {
      addFinding(
        'P1',
        'missing_generated_bundle',
        `${path.relative(PROJECT_ROOT, generatedPath)}: ${error instanceof Error ? error.message : String(error)}`,
      );
      continue;
    }

    if (actual !== expected) {
      addFinding('P1', 'stale_generated_bundle', `${path.relative(PROJECT_ROOT, generatedPath)} is stale`);
    }
  }

  const expectedGeneratedFiles = new Set(localeDirs.map((locale) => `${locale}.json`));
  const generatedFiles = (await readdir(OUTPUT_ROOT, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name);

  for (const fileName of generatedFiles) {
    if (!expectedGeneratedFiles.has(fileName)) {
      addFinding('P1', 'stale_generated_bundle', `${path.relative(PROJECT_ROOT, path.join(OUTPUT_ROOT, fileName))} has no source locale`);
    }
  }
}

async function auditNamespaceMap() {
  for (const fileName of CRITICAL_MESSAGE_FILES) {
    if (!(fileName in MESSAGE_FILE_NAMESPACE_MAP)) {
      addFinding('P0', 'missing_namespace_mapping', `${fileName} is not included in MESSAGE_FILE_NAMESPACE_MAP`);
    }
  }
}

await auditNamespaceMap();
await auditCriticalCoverage();
await auditRussianGlossary();
await auditGeneratedBundlesFreshness();

if (findings.length > 0) {
  process.stderr.write('[i18n-audit] Direct-reviewed localization defects found:\n');
  for (const finding of findings) {
    process.stderr.write(`- ${finding.severity} ${finding.code}: ${finding.message}\n`);
  }
  process.exit(1);
}

process.stdout.write('[i18n-audit] Direct-reviewed ru/en localization coverage and generated bundles are clean.\n');
