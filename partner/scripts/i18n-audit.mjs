import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, '..');
const MESSAGES_ROOT = path.join(PROJECT_ROOT, 'messages');
const GENERATED_ROOT = path.join(PROJECT_ROOT, 'src', 'i18n', 'messages', 'generated');
const DIRECT_REVIEWED_LOCALES = ['en-EN', 'ru-RU'];
const RU_GLOSSARY_REVIEW_FILES = new Set([
  'dashboard.json',
  'language-selector.json',
  'navigation.json',
  'partner.json',
  'sections.json',
]);

const MESSAGE_FILE_NAMESPACE_MAP = {
  'header.json': 'Header',
  'navigation.json': 'Navigation',
  'dashboard.json': 'Dashboard',
  'commerce.json': 'Commerce',
  'customers.json': 'Customers',
  'governance.json': 'Governance',
  'growth.json': 'Growth',
  'integrations.json': 'Integrations',
  'infrastructure.json': 'Infrastructure',
  'security-admin.json': 'AdminSecurity',
  'sections.json': 'Sections',
  'users.json': 'Users',
  'servers.json': 'Servers',
  'placeholder.json': 'Placeholder',
  'users-table.json': 'UsersTable',
  'servers-table.json': 'ServersTable',
  'server-card.json': 'ServerCard',
  'landing.json': 'Landing',
  'footer.json': 'Footer',
  'language-selector.json': 'LanguageSelector',
  'privacy-policy.json': 'PrivacyPolicy',
  'delete-account.json': 'DeleteAccount',
  'auth.json': 'Auth',
  'a11y.json': 'A11y',
  'MiniApp.json': 'MiniApp',
  'settings.json': 'Settings',
  'analytics.json': 'Analytics',
  'monitoring.json': 'Monitoring',
  'subscriptions.json': 'Subscriptions',
  'wallet.json': 'Wallet',
  'payment-history.json': 'PaymentHistory',
  'referral.json': 'Referral',
  'partner.json': 'Partner',
  'devices.json': 'Devices',
  'HelpCenter.json': 'HelpCenter',
  'Docs.json': 'Docs',
  'Contact.json': 'Contact',
  'Status.json': 'Status',
  'Download.json': 'Download',
  'Pricing.json': 'Pricing',
  'Features.json': 'Features',
  'Network.json': 'Network',
  'Api.json': 'Api',
  'Privacy.json': 'Privacy',
  'Terms.json': 'Terms',
  'Security.json': 'Security',
  'storefront.json': 'Storefront',
};

const RU_FORBIDDEN_GLOSSARY = [
  /\bworkspace(?:s)?\b/i,
  /\breview(?:s|ed|ing)?\b/i,
  /\bsurface(?:s)?\b/i,
  /\breadiness(?: gating)?\b/i,
  /\bcanonical data\b/i,
  /\bbackend contract(?:s)?\b/i,
  /\brelease[- ]band\b/i,
  /\brelease[- ]ring\b/i,
];

const PLACEHOLDER_PATTERN = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

function isJsonObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stableSortObject(value) {
  if (Array.isArray(value)) {
    return value.map(stableSortObject);
  }

  if (!isJsonObject(value)) {
    return value;
  }

  return Object.keys(value)
    .sort((left, right) => left.localeCompare(right))
    .reduce((acc, key) => {
      acc[key] = stableSortObject(value[key]);
      return acc;
    }, {});
}

function flatten(value, pathSegments = [], rows = []) {
  if (isJsonObject(value)) {
    for (const [key, child] of Object.entries(value)) {
      flatten(child, [...pathSegments, key], rows);
    }

    return rows;
  }

  if (Array.isArray(value)) {
    value.forEach((child, index) => flatten(child, [...pathSegments, String(index)], rows));
    return rows;
  }

  rows.push({
    path: pathSegments.join('.'),
    value,
  });

  return rows;
}

function collectPlaceholders(value) {
  if (typeof value !== 'string') {
    return [];
  }

  return [...value.matchAll(PLACEHOLDER_PATTERN)]
    .map((match) => match[1])
    .sort((left, right) => left.localeCompare(right));
}

function stripIcuPlaceholders(value) {
  return value.replace(PLACEHOLDER_PATTERN, '');
}

function formatLocation(locale, fileName, keyPath) {
  return `${locale}/${fileName}${keyPath ? `:${keyPath}` : ''}`;
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, 'utf8'));
}

async function getMessageFiles(locale) {
  const entries = await readdir(path.join(MESSAGES_ROOT, locale), { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right));
}

async function readLocaleMessages(locale, fileName) {
  return readJson(path.join(MESSAGES_ROOT, locale, fileName));
}

async function auditCoverageAndPlaceholders(errors) {
  const [enFiles, ruFiles] = await Promise.all(
    DIRECT_REVIEWED_LOCALES.map((locale) => getMessageFiles(locale)),
  );
  const enFileSet = new Set(enFiles);
  const ruFileSet = new Set(ruFiles);

  for (const fileName of enFiles) {
    if (!ruFileSet.has(fileName)) {
      errors.push(`Missing ru-RU message file: ${fileName}`);
    }
  }

  for (const fileName of ruFiles) {
    if (!enFileSet.has(fileName)) {
      errors.push(`Unexpected ru-RU message file without en-EN source: ${fileName}`);
    }
  }

  for (const fileName of enFiles.filter((entry) => ruFileSet.has(entry))) {
    const [enMessages, ruMessages] = await Promise.all([
      readLocaleMessages('en-EN', fileName),
      readLocaleMessages('ru-RU', fileName),
    ]);
    const enRows = flatten(enMessages).sort((left, right) => left.path.localeCompare(right.path));
    const ruRows = flatten(ruMessages).sort((left, right) => left.path.localeCompare(right.path));
    const ruRowMap = new Map(ruRows.map((row) => [row.path, row]));
    const enRowMap = new Map(enRows.map((row) => [row.path, row]));

    for (const row of enRows) {
      const ruRow = ruRowMap.get(row.path);
      if (!ruRow) {
        errors.push(`Missing ru-RU key: ${formatLocation('ru-RU', fileName, row.path)}`);
        continue;
      }

      const enPlaceholders = collectPlaceholders(row.value);
      const ruPlaceholders = collectPlaceholders(ruRow.value);

      if (enPlaceholders.join(',') !== ruPlaceholders.join(',')) {
        errors.push(
          `Placeholder mismatch at ${fileName}:${row.path}: en-EN={${enPlaceholders.join(',')}} ru-RU={${ruPlaceholders.join(',')}}`,
        );
      }
    }

    for (const row of ruRows) {
      if (!enRowMap.has(row.path)) {
        errors.push(`Unexpected ru-RU key: ${formatLocation('ru-RU', fileName, row.path)}`);
      }
    }
  }
}

async function auditRussianGlossary(errors) {
  for (const fileName of RU_GLOSSARY_REVIEW_FILES) {
    const messages = await readLocaleMessages('ru-RU', fileName);
    const rows = flatten(messages);

    for (const row of rows) {
      if (typeof row.value !== 'string') {
        continue;
      }

      const failedPattern = RU_FORBIDDEN_GLOSSARY.find((pattern) => pattern.test(stripIcuPlaceholders(row.value)));

      if (failedPattern) {
        errors.push(
          `Forbidden RU glossary term at ${formatLocation('ru-RU', fileName, row.path)}: ${row.value}`,
        );
      }
    }
  }
}

async function buildLocaleBundle(locale) {
  const bundle = {};

  for (const [fileName, namespace] of Object.entries(MESSAGE_FILE_NAMESPACE_MAP)) {
    bundle[namespace] = await readLocaleMessages(locale, fileName);
  }

  return stableSortObject(bundle);
}

async function auditGeneratedBundles(errors) {
  for (const locale of DIRECT_REVIEWED_LOCALES) {
    const expected = `${JSON.stringify(await buildLocaleBundle(locale), null, 2)}\n`;
    const generatedPath = path.join(GENERATED_ROOT, `${locale}.json`);
    const actual = await readFile(generatedPath, 'utf8').catch((error) => {
      if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
        return null;
      }

      throw error;
    });

    if (actual === null) {
      errors.push(`Missing generated bundle: ${path.relative(PROJECT_ROOT, generatedPath)}`);
      continue;
    }

    if (actual !== expected) {
      errors.push(`Stale generated bundle: ${path.relative(PROJECT_ROOT, generatedPath)}. Run npm run prepare:i18n.`);
    }
  }
}

const errors = [];

await auditCoverageAndPlaceholders(errors);
await auditRussianGlossary(errors);
await auditGeneratedBundles(errors);

if (errors.length > 0) {
  console.error(`[i18n-audit] Failed with ${errors.length} issue(s):`);
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

process.stdout.write('[i18n-audit] Direct-reviewed ru/en coverage, placeholders, glossary, and generated bundles are clean.\n');
