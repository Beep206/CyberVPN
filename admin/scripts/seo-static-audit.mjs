#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { rm } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createServer } from 'node:net';
import { join, resolve } from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = fileURLToPath(new URL('.', import.meta.url));
const FRONTEND_ROOT = resolve(SCRIPT_DIR, '..');
const require = createRequire(import.meta.url);
const NEXT_CLI_PATH = require.resolve('next/dist/bin/next');

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || 'https://admin.ozoxy.ru').replace(/\/+$/, '');
const DEFAULT_LOCALE = 'ru-RU';
const RTL_LOCALE = 'ar-SA';
const PRIORITY_LOCALE = 'ru-RU';
const CHINA_LOCALE = 'zh-CN';
const INDIA_LOCALE = 'hi-IN';
const JAPAN_LOCALE = 'ja-JP';
const SERVER_HOST = '127.0.0.1';
const AUDIT_DIST_DIR = '.next-seo-audit';
const STARTUP_TIMEOUT_MS = 30_000;
const BUILD_TIMEOUT_MS = 10 * 60_000;
const REQUEST_TIMEOUT_MS = 15_000;
const HEALTHCHECK_TIMEOUT_MS = 5_000;

const INDEXABLE_ROUTES = [
  '/',
  '/api',
  '/audits',
  '/compare',
  '/contact',
  '/devices',
  '/docs',
  '/download',
  '/features',
  '/guides',
  '/help',
  '/network',
  '/pricing',
  '/privacy',
  '/privacy-policy',
  '/security',
  '/status',
  '/terms',
  '/trust',
];

const CONTENT_ROUTE_SAMPLES = [
  '/guides/how-to-bypass-dpi-with-vless-reality',
  '/compare/vless-reality-vs-wireguard',
  '/devices/android-vpn-setup',
];

const PRIVATE_ROUTE_SAMPLES = [
  '/analytics',
  '/dashboard',
  '/login',
  '/miniapp',
  '/partner',
  '/wallet',
  '/test-animation',
  '/test-error',
];

const errors = [];

function assert(condition, message) {
  if (!condition) {
    errors.push(message);
  }
}

function delay(ms) {
  return new Promise((resolveDelay) => {
    setTimeout(resolveDelay, ms);
  });
}

function buildLocalizedRoute(route, locale = DEFAULT_LOCALE) {
  return route === '/' ? `/${locale}` : `/${locale}${route}`;
}

function buildExpectedUrl(locale, route) {
  return route === '/' ? `${SITE_URL}/${locale}` : `${SITE_URL}/${locale}${route}`;
}

function getCanonical(html) {
  return html.match(/<link rel="canonical" href="([^"]+)"/i)?.[1];
}

function getRobots(html) {
  return html.match(/<meta name="robots" content="([^"]+)"/i)?.[1];
}

function getHtmlTag(html) {
  return html.match(/<html[^>]*lang="([^"]+)"[^>]*dir="([^"]+)"/i);
}

function getJsonLdBlocks(html) {
  return [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/gi)].map(
    ([, json]) => json,
  );
}

async function getAvailablePort() {
  return new Promise((resolvePort, rejectPort) => {
    const server = createServer();

    server.on('error', rejectPort);
    server.listen(0, SERVER_HOST, () => {
      const address = server.address();

      if (!address || typeof address === 'string') {
        rejectPort(new Error('Failed to allocate an available port for SEO audit.'));
        return;
      }

      server.close((error) => {
        if (error) {
          rejectPort(error);
          return;
        }

        resolvePort(address.port);
      });
    });
  });
}

function createLogCollector() {
  let output = '';

  return {
    append(chunk) {
      output = `${output}${chunk}`;

      if (output.length > 20_000) {
        output = output.slice(-20_000);
      }
    },
    read() {
      return output.trim();
    },
  };
}

async function runBuild() {
  const logCollector = createLogCollector();
  const child = spawn(
    process.execPath,
    [NEXT_CLI_PATH, 'build', '--webpack'],
    {
      cwd: FRONTEND_ROOT,
      env: {
        ...process.env,
        NEXT_DIST_DIR: AUDIT_DIST_DIR,
        NEXT_TELEMETRY_DISABLED: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  child.stdout?.setEncoding('utf8');
  child.stderr?.setEncoding('utf8');
  child.stdout?.on('data', (chunk) => {
    logCollector.append(chunk);
  });
  child.stderr?.on('data', (chunk) => {
    logCollector.append(chunk);
  });

  const exitCode = await Promise.race([
    new Promise((resolveExit) => {
      child.once('exit', resolveExit);
    }),
    delay(BUILD_TIMEOUT_MS).then(() => {
      if (child.exitCode === null) {
        child.kill('SIGKILL');
      }

      return 'timeout';
    }),
  ]);

  if (exitCode !== 0) {
    throw new Error(
      [
        exitCode === 'timeout'
          ? `SEO audit build timed out after ${BUILD_TIMEOUT_MS}ms.`
          : `SEO audit build failed with code ${exitCode}.`,
        logCollector.read(),
      ]
        .filter(Boolean)
        .join('\n\n'),
    );
  }
}

function startServer(port) {
  const logCollector = createLogCollector();
  const child = spawn(
    process.execPath,
    [NEXT_CLI_PATH, 'start', '--port', `${port}`, '--hostname', SERVER_HOST],
    {
      cwd: FRONTEND_ROOT,
      env: {
        ...process.env,
        NEXT_DIST_DIR: AUDIT_DIST_DIR,
        NEXT_TELEMETRY_DISABLED: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  child.stdout?.setEncoding('utf8');
  child.stderr?.setEncoding('utf8');
  child.stdout?.on('data', (chunk) => {
    logCollector.append(chunk);
  });
  child.stderr?.on('data', (chunk) => {
    logCollector.append(chunk);
  });

  return { child, logCollector };
}

async function waitForServer(baseUrl, child, logCollector) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < STARTUP_TIMEOUT_MS) {
    if (child.exitCode !== null) {
      throw new Error(
        [
          `SEO audit server exited before readiness with code ${child.exitCode}.`,
          logCollector.read(),
        ]
          .filter(Boolean)
          .join('\n\n'),
      );
    }

    try {
      const response = await fetch(`${baseUrl}${buildLocalizedRoute('/')}`, {
        redirect: 'manual',
        signal: AbortSignal.timeout(HEALTHCHECK_TIMEOUT_MS),
      });

      if (response.status < 500) {
        return;
      }
    } catch {
      // Wait for the local production server to finish booting.
    }

    await delay(250);
  }

  throw new Error(
    [
      `Timed out after ${STARTUP_TIMEOUT_MS}ms waiting for SEO audit server readiness.`,
      logCollector.read(),
    ]
      .filter(Boolean)
      .join('\n\n'),
  );
}

async function stopServer(child) {
  if (child.exitCode !== null) {
    return;
  }

  child.kill('SIGTERM');

  await Promise.race([
    new Promise((resolveStop) => {
      child.once('exit', resolveStop);
    }),
    delay(5_000).then(() => {
      if (child.exitCode === null) {
        child.kill('SIGKILL');
      }
    }),
  ]);
}

async function fetchText(baseUrl, pathname) {
  const response = await fetch(`${baseUrl}${pathname}`, {
    redirect: 'follow',
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  assert(response.ok, `Expected "${pathname}" to return 2xx, got ${response.status}`);

  return response.text();
}

function assertPublicPage(route, html) {
  const expectedUrl = buildExpectedUrl(DEFAULT_LOCALE, route);
  const expectedSocialImageUrl = buildExpectedUrl(DEFAULT_LOCALE, '/opengraph-image');

  assert(html.length > 0, `Public page is empty for route "${route}"`);
  assert(
    getCanonical(html) === expectedUrl,
    `Wrong canonical for "${route}": expected ${expectedUrl}, got ${getCanonical(html) ?? 'none'}`,
  );
  assert(
    html.includes(`hrefLang="${DEFAULT_LOCALE}" href="${expectedUrl}"`),
    `Missing self hreflang for "${route}"`,
  );
  assert(
    html.includes(`hrefLang="x-default" href="${buildExpectedUrl(DEFAULT_LOCALE, route)}"`),
    `Missing x-default hreflang for "${route}"`,
  );
  assert(
    html.includes(expectedSocialImageUrl),
    `Missing production social image URL for "${route}"`,
  );

  if (route !== '/') {
    assert(
      getCanonical(html) !== `${SITE_URL}/${DEFAULT_LOCALE}`,
      `Deep page "${route}" canonicalized to locale root`,
    );
  }
}

function assertLocalizedPublicPage(route, locale, html) {
  const expectedUrl = buildExpectedUrl(locale, route);
  const expectedSocialImageUrl = buildExpectedUrl(locale, '/opengraph-image');

  assert(html.length > 0, `Localized public page is empty for route "${route}" and locale "${locale}"`);
  assert(
    getCanonical(html) === expectedUrl,
    `Wrong canonical for "${route}" and locale "${locale}": expected ${expectedUrl}, got ${getCanonical(html) ?? 'none'}`,
  );
  assert(
    html.includes(`hrefLang="${locale}" href="${expectedUrl}"`),
    `Missing self hreflang for "${route}" and locale "${locale}"`,
  );
  assert(
    getRobots(html) !== 'noindex, nofollow',
    `Localized public page "${route}" and locale "${locale}" must stay indexable`,
  );
  assert(
    html.includes(expectedSocialImageUrl),
    `Localized public page "${route}" and locale "${locale}" must use a locale-aware social image`,
  );
}

function assertPrivatePage(route, html) {
  const robots = getRobots(html);

  assert(html.length > 0, `Private page is empty for route "${route}"`);
  assert(
    robots === 'noindex, nofollow',
    `Private page "${route}" must be noindex, got ${robots ?? 'none'}`,
  );
  assert(!html.includes('rel="canonical"'), `Private page "${route}" must not emit canonical`);
  assert(!html.includes('hrefLang='), `Private page "${route}" must not emit hreflang tags`);
}

function assertRobots(robots) {
  assert(robots.length > 0, 'robots.txt response must not be empty');
  assert(robots.includes('Allow: /'), 'robots.txt must allow "/"');
  assert(
    robots.includes(`Sitemap: ${SITE_URL}/sitemap.xml`),
    'robots.txt must point to the production sitemap URL',
  );
  assert(
    robots.includes(`Disallow: /${DEFAULT_LOCALE}/analytics`) &&
      robots.includes(`Disallow: /${DEFAULT_LOCALE}/wallet`),
    'robots.txt must disallow localized dashboard-related client routes',
  );
  assert(
    robots.includes(`Disallow: /${DEFAULT_LOCALE}/dashboard`),
    'robots.txt must disallow localized dashboard routes',
  );
  assert(
    robots.includes(`Disallow: /${DEFAULT_LOCALE}/test-animation`),
    'robots.txt must disallow localized test routes',
  );
  assert(
    !robots.includes('vpn-admin.example.com'),
    'robots.txt must not reference vpn-admin.example.com',
  );
}

function assertSitemapRoute(xml) {
  assert(xml.length > 0, 'sitemap.xml response must not be empty');
  assert(
    xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}`),
    'sitemap.xml must include the localized homepage URL',
  );
  assert(
    xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/help`),
    'sitemap.xml must include the help knowledge surface',
  );
  assert(
    xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/docs`),
    'sitemap.xml must include the docs knowledge surface',
  );
  assert(
    xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/guides`),
    'sitemap.xml must include the guides hub',
  );
  assert(
    xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/guides/how-to-bypass-dpi-with-vless-reality`),
    'sitemap.xml must include the guide detail route',
  );
  assert(
    xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/trust`),
    'sitemap.xml must include the trust center route',
  );
  assert(!xml.includes('/dashboard'), 'sitemap.xml must not include dashboard URLs');
  assert(
    !xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/analytics`) &&
      !xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/wallet`) &&
      !xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/settings`) &&
      !xml.includes(`${SITE_URL}/${DEFAULT_LOCALE}/users`),
    'sitemap.xml must not include dashboard-related client URLs',
  );
  assert(!xml.includes('/login'), 'sitemap.xml must not include auth URLs');
  assert(
    !xml.includes('/test-animation') && !xml.includes('/test-error'),
    'sitemap.xml must not include test URLs',
  );
  assert(
    xml.includes(`${SITE_URL}/${PRIORITY_LOCALE}/guides`) &&
      xml.includes(`${SITE_URL}/${CHINA_LOCALE}/trust`),
    'sitemap.xml must include priority-market hub and trust routes',
  );
  assert(
    xml.includes(`${SITE_URL}/${PRIORITY_LOCALE}/guides/how-to-bypass-dpi-with-vless-reality`) &&
      xml.includes(`${SITE_URL}/${CHINA_LOCALE}/compare/vless-reality-vs-wireguard`) &&
      xml.includes(`${SITE_URL}/${PRIORITY_LOCALE}/devices/android-vpn-setup`) &&
      xml.includes(`${SITE_URL}/${INDIA_LOCALE}/guides/how-to-bypass-dpi-with-vless-reality`) &&
      xml.includes(`${SITE_URL}/${JAPAN_LOCALE}/devices/android-vpn-setup`),
    'sitemap.xml must include localized detail routes for the full priority-market rollout',
  );
  assert(
    !xml.includes(`${SITE_URL}/fa-IR/guides/how-to-bypass-dpi-with-vless-reality`) &&
      !xml.includes(`${SITE_URL}/ar-SA/devices/android-vpn-setup`),
    'sitemap.xml must keep non-priority localized detail-content combinations out of the index',
  );
  assert(
    !xml.includes('vpn-admin.example.com'),
    'sitemap.xml must not reference vpn-admin.example.com',
  );
}

function assertHomeJsonLdAndCtas(homeHtml) {
  const jsonLd = getJsonLdBlocks(homeHtml).join('\n');

  assert(!jsonLd.includes('SearchAction'), 'Homepage JSON-LD must not advertise SearchAction');
  assert(!jsonLd.includes('/search'), 'Homepage JSON-LD must not point to a fake /search route');
  assert(
    homeHtml.includes('https://t.me/cybervpn_bot'),
    'Homepage prerender output must include the Telegram acquisition URL',
  );
  assert(
    homeHtml.includes('/download'),
    'Homepage prerender output must include the download route',
  );
  assert(
    homeHtml.includes('https://t.me/cybervpn'),
    'Homepage prerender output must include the brand entity URL',
  );
}

function assertKnowledgeStructuredData(helpHtml, docsHtml, guideHtml, compareHtml, deviceHtml) {
  const helpJsonLd = getJsonLdBlocks(helpHtml).join('\n');
  const docsJsonLd = getJsonLdBlocks(docsHtml).join('\n');
  const guideJsonLd = getJsonLdBlocks(guideHtml).join('\n');
  const compareJsonLd = getJsonLdBlocks(compareHtml).join('\n');
  const deviceJsonLd = getJsonLdBlocks(deviceHtml).join('\n');

  assert(helpJsonLd.includes('"@type":"FAQPage"'), 'Help page must emit FAQPage JSON-LD');
  assert(
    helpJsonLd.includes('"@type":"BreadcrumbList"'),
    'Help page must emit BreadcrumbList JSON-LD',
  );
  assert(
    docsJsonLd.includes('"@type":"TechArticle"'),
    'Docs page must emit TechArticle JSON-LD',
  );
  assert(
    docsJsonLd.includes('"@type":"BreadcrumbList"'),
    'Docs page must emit BreadcrumbList JSON-LD',
  );
  assert(
    guideJsonLd.includes('"@type":"TechArticle"'),
    'Guide detail page must emit TechArticle JSON-LD',
  );
  assert(
    compareJsonLd.includes('"@type":"TechArticle"'),
    'Compare detail page must emit TechArticle JSON-LD',
  );
  assert(
    deviceJsonLd.includes('"@type":"SoftwareApplication"'),
    'Device detail page must emit SoftwareApplication JSON-LD',
  );
}

function assertRtlMarkup(rtlHtml) {
  const htmlTag = getHtmlTag(rtlHtml);

  assert(
    htmlTag?.[1] === RTL_LOCALE && htmlTag?.[2] === 'rtl',
    `RTL page must render lang="${RTL_LOCALE}" dir="rtl"`,
  );
}

function assertNoLegacyDomainLeak(artifacts) {
  for (const artifact of artifacts) {
    assert(
      !artifact.includes('vpn-admin.example.com'),
      'SEO artifacts must not reference vpn-admin.example.com',
    );
    assert(
      !artifact.includes('http://localhost:3001'),
      'SEO artifacts must not leak localhost URLs',
    );
  }
}

async function main() {
  await rm(join(FRONTEND_ROOT, AUDIT_DIST_DIR), { recursive: true, force: true });
  await runBuild();

  const port = await getAvailablePort();
  const baseUrl = `http://${SERVER_HOST}:${port}`;
  const { child, logCollector } = startServer(port);

  try {
    await waitForServer(baseUrl, child, logCollector);

    const publicRoutesToFetch = [...INDEXABLE_ROUTES, ...CONTENT_ROUTE_SAMPLES];
    const publicPageEntries = await Promise.all(
      publicRoutesToFetch.map(async (route) => [route, await fetchText(baseUrl, buildLocalizedRoute(route))]),
    );
    const privatePageEntries = await Promise.all(
      PRIVATE_ROUTE_SAMPLES.map(async (route) => [route, await fetchText(baseUrl, buildLocalizedRoute(route))]),
    );
    const [
      robots,
      sitemapXml,
      rtlHtml,
      russianGuidesHtml,
      chineseTrustHtml,
      russianGuideDetailHtml,
      chineseCompareDetailHtml,
      russianDeviceDetailHtml,
      indianGuideDetailHtml,
      japaneseDeviceDetailHtml,
    ] = await Promise.all([
      fetchText(baseUrl, '/robots.txt'),
      fetchText(baseUrl, '/sitemap.xml'),
      fetchText(baseUrl, buildLocalizedRoute('/pricing', RTL_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/guides', PRIORITY_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/trust', CHINA_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/guides/how-to-bypass-dpi-with-vless-reality', PRIORITY_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/compare/vless-reality-vs-wireguard', CHINA_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/devices/android-vpn-setup', PRIORITY_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/guides/how-to-bypass-dpi-with-vless-reality', INDIA_LOCALE)),
      fetchText(baseUrl, buildLocalizedRoute('/devices/android-vpn-setup', JAPAN_LOCALE)),
    ]);

    const publicPages = new Map(publicPageEntries);
    const privatePages = new Map(privatePageEntries);
    const homeHtml = publicPages.get('/');
    const helpHtml = publicPages.get('/help');
    const docsHtml = publicPages.get('/docs');
    const pricingHtml = publicPages.get('/pricing');
    const guideHtml = publicPages.get('/guides/how-to-bypass-dpi-with-vless-reality');
    const compareHtml = publicPages.get('/compare/vless-reality-vs-wireguard');
    const deviceHtml = publicPages.get('/devices/android-vpn-setup');

    for (const route of INDEXABLE_ROUTES) {
      assertPublicPage(route, publicPages.get(route) ?? '');
    }

    for (const route of CONTENT_ROUTE_SAMPLES) {
      assertPublicPage(route, publicPages.get(route) ?? '');
    }

    for (const route of PRIVATE_ROUTE_SAMPLES) {
      assertPrivatePage(route, privatePages.get(route) ?? '');
    }

    if (homeHtml && helpHtml && docsHtml && pricingHtml && guideHtml && compareHtml && deviceHtml) {
      assertRobots(robots);
      assertSitemapRoute(sitemapXml);
      assertHomeJsonLdAndCtas(homeHtml);
      assertKnowledgeStructuredData(helpHtml, docsHtml, guideHtml, compareHtml, deviceHtml);
      assertLocalizedPublicPage('/guides', PRIORITY_LOCALE, russianGuidesHtml);
      assertLocalizedPublicPage('/trust', CHINA_LOCALE, chineseTrustHtml);
      assertLocalizedPublicPage(
        '/guides/how-to-bypass-dpi-with-vless-reality',
        PRIORITY_LOCALE,
        russianGuideDetailHtml,
      );
      assertLocalizedPublicPage(
        '/compare/vless-reality-vs-wireguard',
        CHINA_LOCALE,
        chineseCompareDetailHtml,
      );
      assertLocalizedPublicPage(
        '/devices/android-vpn-setup',
        PRIORITY_LOCALE,
        russianDeviceDetailHtml,
      );
      assertLocalizedPublicPage(
        '/guides/how-to-bypass-dpi-with-vless-reality',
        INDIA_LOCALE,
        indianGuideDetailHtml,
      );
      assertLocalizedPublicPage(
        '/devices/android-vpn-setup',
        JAPAN_LOCALE,
        japaneseDeviceDetailHtml,
      );
      assertRtlMarkup(rtlHtml);
      assertNoLegacyDomainLeak([
        homeHtml,
        helpHtml,
        docsHtml,
        pricingHtml,
        guideHtml,
        compareHtml,
        deviceHtml,
        russianGuidesHtml,
        chineseTrustHtml,
        russianGuideDetailHtml,
        chineseCompareDetailHtml,
        russianDeviceDetailHtml,
        indianGuideDetailHtml,
        japaneseDeviceDetailHtml,
        robots,
        sitemapXml,
      ]);
    }
  } finally {
    await stopServer(child);
  }
}

await main().catch((error) => {
  console.error('SEO static audit failed.\n');
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

if (errors.length > 0) {
  console.error('SEO static audit failed.\n');

  for (const [index, error] of errors.entries()) {
    console.error(`${index + 1}. ${error}`);
  }

  process.exit(1);
}

process.stdout.write(
  `SEO static audit passed: ${INDEXABLE_ROUTES.length + CONTENT_ROUTE_SAMPLES.length} public routes and ${PRIVATE_ROUTE_SAMPLES.length} private route samples verified.\n`,
);
