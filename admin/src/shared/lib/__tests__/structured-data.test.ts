import { describe, expect, it } from 'vitest';
import {
  buildBreadcrumbListStructuredData,
  buildFaqPageStructuredData,
  buildOfferStructuredData,
  buildSoftwareApplicationStructuredData,
  buildTechArticleStructuredData,
} from '@/shared/lib/structured-data';
import { SITE_URL } from '@/shared/lib/site-metadata';

const SENSITIVE_SCHEMA_VALUE_PATTERN =
  /\b(?:Bearer\s+[A-Za-z0-9._-]+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|access_token|refresh_token|customer_access_token|partner_access_token|vless:\/\/|vmess:\/\/|trojan:\/\/|ss:\/\/|wireguard:\/\/|https?:\/\/(?:localhost|127\.0\.0\.1|portal\.localhost|storefront\.localhost)(?::\d+)?)\b/i;
const SENSITIVE_SCHEMA_KEY_PATTERN =
  /^(?:accessToken|refreshToken|authorization|cookie|password|secret|session|jwt|credential|userId|customerId|partnerId|subscriptionUrl|vpnUrl)$/i;
const PLACEHOLDER_SCHEMA_VALUES = new Set(['undefined', 'null', 'nan', '[object object]']);

function expectStructuredDataSerializable(value: unknown) {
  const serialized = JSON.stringify(value);
  expect(serialized).toBeTruthy();

  const parsed = JSON.parse(serialized) as unknown;

  expectSchemaValueSafe(parsed);
}

function expectSchemaValueSafe(value: unknown) {
  expect(value).not.toBeNull();

  if (typeof value === 'string') {
    expect(PLACEHOLDER_SCHEMA_VALUES.has(value.trim().toLowerCase())).toBe(false);
    expect(value).not.toMatch(SENSITIVE_SCHEMA_VALUE_PATTERN);
    return;
  }

  if (Array.isArray(value)) {
    value.forEach(expectSchemaValueSafe);
    return;
  }

  if (typeof value === 'object' && value !== null) {
    for (const [key, entry] of Object.entries(value)) {
      expect(key).not.toMatch(SENSITIVE_SCHEMA_KEY_PATTERN);
      expectSchemaValueSafe(entry);
    }
  }
}

describe('structured-data helpers', () => {
  it('builds localized FAQPage structured data from server FAQ content', () => {
    const data = buildFaqPageStructuredData({
      locale: 'ru-RU',
      path: '/help',
      title: 'Help Center',
      description: 'Server-rendered VPN help answers.',
      faqs: [
        {
          question: 'How do I connect?',
          answer: 'Install the client and use your token.',
        },
        {
          question: 'Is there a kill switch?',
          answer: 'Yes, it blocks traffic when the tunnel drops.',
        },
      ],
    });

    expect(data['@type']).toBe('FAQPage');
    expect(data.url).toBe(`${SITE_URL}/ru-RU/help`);
    expect(data.inLanguage).toBe('ru-RU');
    expect(data.mainEntity).toHaveLength(2);
    const mainEntity = data.mainEntity;
    if (!Array.isArray(mainEntity)) {
      throw new Error('Expected FAQ mainEntity to be an array');
    }
    expect(mainEntity[0]).toMatchObject({
      '@type': 'Question',
      name: 'How do I connect?',
    });
  });

  it('builds breadcrumb structured data on the production domain', () => {
    const data = buildBreadcrumbListStructuredData({
      locale: 'en-EN',
      items: [
        { name: 'Home', path: '/' },
        { name: 'Docs', path: '/docs' },
      ],
    });

    expect(data['@type']).toBe('BreadcrumbList');
    expect(data.itemListElement).toEqual([
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Home',
        item: `${SITE_URL}/en-EN`,
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'Docs',
        item: `${SITE_URL}/en-EN/docs`,
      },
    ]);
  });

  it('builds TechArticle structured data for the docs knowledge surface', () => {
    const data = buildTechArticleStructuredData({
      locale: 'en-EN',
      path: '/docs',
      title: 'Neural Documentation',
      description: 'Technical VPN setup and integration docs.',
      sections: ['INITIALIZATION', 'SIGNAL ROUTING', 'ENCRYPTION PROTOCOLS', 'NEURAL API'],
    });

    expect(data['@type']).toBe('TechArticle');
    expect(data.url).toBe(`${SITE_URL}/en-EN/docs`);
    expect(data.articleSection).toEqual([
      'INITIALIZATION',
      'SIGNAL ROUTING',
      'ENCRYPTION PROTOCOLS',
      'NEURAL API',
    ]);
    expect(data.publisher).toMatchObject({
      '@type': 'Organization',
      name: 'CyberVPN',
    });
  });

  it('builds offer structured data on the localized production domain', () => {
    const data = buildOfferStructuredData({
      locale: 'en-EN',
      name: 'CYBER_PRO',
      description: 'Unlimited bandwidth and stealth routing.',
      price: '8.99',
      url: '/pricing',
    });

    expect(data).toMatchObject({
      '@type': 'Offer',
      name: 'CYBER_PRO',
      price: '8.99',
      priceCurrency: 'USD',
      url: `${SITE_URL}/en-EN/pricing`,
    });
  });

  it('builds SoftwareApplication structured data with visible feature and offer coverage', () => {
    const data = buildSoftwareApplicationStructuredData({
      locale: 'en-EN',
      path: '/download',
      title: 'CyberVPN',
      description: 'Install the secure client on every major platform.',
      applicationCategory: 'SecurityApplication',
      operatingSystems: ['Windows', 'macOS', 'Linux', 'iOS', 'Android'],
      featureList: ['Reality masking', '10 Gbps backbone', 'Multi-platform access'],
      downloadPath: '/download',
      offers: [
        {
          name: 'STEALTH',
          description: 'Entry access to the secure network.',
          price: '0',
          url: '/pricing',
        },
      ],
    });

    expect(data['@type']).toBe('SoftwareApplication');
    expect(data.url).toBe(`${SITE_URL}/en-EN/download`);
    expect(data.downloadUrl).toBe(`${SITE_URL}/en-EN/download`);
    expect(data.featureList).toEqual([
      'Reality masking',
      '10 Gbps backbone',
      'Multi-platform access',
    ]);
    expect(data.offers).toMatchObject([
      {
        '@type': 'Offer',
        price: '0',
        url: `${SITE_URL}/en-EN/pricing`,
      },
    ]);
  });

  it('serializes schema-dts payloads without placeholders or runtime secrets', () => {
    const samples = [
      buildBreadcrumbListStructuredData({
        locale: 'en-EN',
        items: [{ name: 'Home', path: '/' }],
      }),
      buildFaqPageStructuredData({
        locale: 'en-EN',
        path: '/help',
        title: 'Help Center',
        description: 'Public help answers.',
        faqs: [{ question: 'How do I connect?', answer: 'Install the client.' }],
      }),
      buildTechArticleStructuredData({
        locale: 'en-EN',
        path: '/docs',
        title: 'Docs',
        description: 'Public documentation.',
        sections: ['Setup'],
      }),
      buildOfferStructuredData({
        locale: 'en-EN',
        name: 'STEALTH',
        description: 'Public plan summary.',
        price: '0',
        url: '/pricing',
      }),
      buildSoftwareApplicationStructuredData({
        locale: 'en-EN',
        path: '/download',
        title: 'CyberVPN',
        description: 'Install the client.',
        applicationCategory: 'SecurityApplication',
        operatingSystems: ['Windows'],
        featureList: ['Reality masking'],
        downloadPath: '/download',
      }),
    ];

    samples.forEach(expectStructuredDataSerializable);
  });
});
