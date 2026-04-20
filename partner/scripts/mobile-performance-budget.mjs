import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const NEXT_OUTPUT_DIR = path.resolve(process.cwd(), '.next');
const ROUTE_STATS_PATH = path.join(
  NEXT_OUTPUT_DIR,
  'diagnostics',
  'route-bundle-stats.json',
);

const ROUTE_BUDGETS = [
  { route: '/[locale]/dashboard', label: 'dashboard', maxGzipKb: 525 },
  { route: '/[locale]/features', label: 'features', maxGzipKb: 500 },
  { route: '/[locale]/pricing', label: 'pricing', maxGzipKb: 500 },
  { route: '/[locale]/privacy', label: 'privacy', maxGzipKb: 500 },
  { route: '/[locale]/download', label: 'download', maxGzipKb: 500 },
  { route: '/[locale]/contact', label: 'contact', maxGzipKb: 540 },
  { route: '/[locale]/docs', label: 'docs', maxGzipKb: 850 },
  { route: '/[locale]/api', label: 'api', maxGzipKb: 500 },
  { route: '/[locale]/login', label: 'login', maxGzipKb: 500 },
  { route: '/[locale]/register', label: 'register', maxGzipKb: 500 },
  { route: '/[locale]/forgot-password', label: 'forgot-password', maxGzipKb: 500 },
  { route: '/[locale]/miniapp/home', label: 'miniapp-home', maxGzipKb: 430 },
];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function gzipSizeInBytes(filePath) {
  return zlib.gzipSync(fs.readFileSync(filePath)).length;
}

function formatKb(bytes) {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function writeLine(message = '') {
  process.stdout.write(`${message}\n`);
}

if (!fs.existsSync(ROUTE_STATS_PATH)) {
  console.error(
    `Missing build diagnostics at ${ROUTE_STATS_PATH}. Run "npm run build" before checking mobile budgets.`,
  );
  process.exit(1);
}

const routeStats = readJson(ROUTE_STATS_PATH);
const failures = [];

writeLine('Mobile performance budgets');

for (const budget of ROUTE_BUDGETS) {
  const entry = routeStats.find((item) => item.route === budget.route);

  if (!entry) {
    failures.push(`${budget.route}: route is missing from route-bundle-stats.json`);
    continue;
  }

  const gzipBytes = entry.firstLoadChunkPaths.reduce((sum, chunkPath) => {
    const fullPath = path.join(
      NEXT_OUTPUT_DIR,
      chunkPath.replace(/^\.next\//, ''),
    );
    return sum + gzipSizeInBytes(fullPath);
  }, 0);

  const maxBytes = budget.maxGzipKb * 1024;
  const status = gzipBytes <= maxBytes ? 'PASS' : 'FAIL';

  writeLine(
    `${status} ${budget.label.padEnd(16)} route=${budget.route} gzip=${formatKb(gzipBytes)} budget=${budget.maxGzipKb.toFixed(1)} KB`,
  );

  if (gzipBytes > maxBytes) {
    failures.push(
      `${budget.route}: gzip first-load JS ${formatKb(gzipBytes)} exceeds ${budget.maxGzipKb.toFixed(1)} KB`,
    );
  }
}

if (failures.length > 0) {
  console.error('\nMobile performance budget failures:');
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

writeLine('\nAll monitored mobile budgets are within limits.');
