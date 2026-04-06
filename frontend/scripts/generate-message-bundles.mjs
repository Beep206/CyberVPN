import { mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { watch as watchFs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, '..');
const MESSAGES_ROOT = path.join(PROJECT_ROOT, 'messages');
const OUTPUT_ROOT = path.join(PROJECT_ROOT, 'src', 'i18n', 'messages', 'generated');

const MESSAGE_FILE_NAMESPACE_MAP = {
  'header.json': 'Header',
  'navigation.json': 'Navigation',
  'dashboard.json': 'Dashboard',
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
};

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

async function getLocaleDirectories() {
  const entries = await readdir(MESSAGES_ROOT, { withFileTypes: true });

  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right));
}

async function readMessageFile(locale, fileName) {
  const filePath = path.join(MESSAGES_ROOT, locale, fileName);

  try {
    const fileContents = await readFile(filePath, 'utf8');
    return JSON.parse(fileContents);
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
      return {};
    }

    throw error;
  }
}

async function buildLocaleBundle(locale) {
  const bundle = {};

  for (const [fileName, namespace] of Object.entries(MESSAGE_FILE_NAMESPACE_MAP)) {
    bundle[namespace] = await readMessageFile(locale, fileName);
  }

  return stableSortObject(bundle);
}

async function removeStaleBundles(currentLocales) {
  try {
    const outputEntries = await readdir(OUTPUT_ROOT, { withFileTypes: true });

    await Promise.all(
      outputEntries
        .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
        .filter((entry) => !currentLocales.has(entry.name.replace(/\.json$/, '')))
        .map((entry) => rm(path.join(OUTPUT_ROOT, entry.name))),
    );
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
      return;
    }

    throw error;
  }
}

async function buildBundles() {
  await mkdir(OUTPUT_ROOT, { recursive: true });

  const locales = await getLocaleDirectories();
  await removeStaleBundles(new Set(locales));

  await Promise.all(
    locales.map(async (locale) => {
      const bundle = await buildLocaleBundle(locale);
      const outputPath = path.join(OUTPUT_ROOT, `${locale}.json`);
      await writeFile(outputPath, `${JSON.stringify(bundle, null, 2)}\n`, 'utf8');
    }),
  );

  process.stdout.write(`[i18n] Generated ${locales.length} locale bundles in ${path.relative(PROJECT_ROOT, OUTPUT_ROOT)}.\n`);
}

function debounce(callback, delayMs) {
  let timeoutId = null;

  return () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      timeoutId = null;
      void callback();
    }, delayMs);
  };
}

async function watchBundles() {
  await buildBundles();

  let watchers = [];
  let isRebuilding = false;
  let shouldRebuildAgain = false;

  const closeWatchers = () => {
    watchers.forEach((currentWatcher) => currentWatcher.close());
    watchers = [];
  };

  const rebuild = async () => {
    if (isRebuilding) {
      shouldRebuildAgain = true;
      return;
    }

    isRebuilding = true;

    try {
      await buildBundles();
      closeWatchers();
      await registerWatchers();
    } catch (error) {
      console.error('[i18n] Failed to rebuild locale bundles.', error);
    } finally {
      isRebuilding = false;
      if (shouldRebuildAgain) {
        shouldRebuildAgain = false;
        await rebuild();
      }
    }
  };

  const scheduleRebuild = debounce(rebuild, 120);

  async function registerWatchers() {
    const localeDirectories = await getLocaleDirectories();
    const watchedDirectories = [MESSAGES_ROOT, ...localeDirectories.map((locale) => path.join(MESSAGES_ROOT, locale))];

    watchers = watchedDirectories.map((directory) =>
      watchFs(directory, { persistent: true }, () => {
        scheduleRebuild();
      }),
    );
  }

  await registerWatchers();

  process.stdout.write('[i18n] Watching source message files for changes.\n');

  const shutdown = () => {
    closeWatchers();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  await new Promise(() => null);
}

const args = new Set(process.argv.slice(2));

if (args.has('--watch')) {
  await watchBundles();
} else {
  await buildBundles();
}
