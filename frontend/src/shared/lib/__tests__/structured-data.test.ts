import { describe, expect, it } from 'vitest';
import {
  buildBreadcrumbListStructuredData,
  buildFaqPageStructuredData,
  buildOfferStructuredData,
  buildSoftwareApplicationStructuredData,
  buildTechArticleStructuredData,
} from '@/shared/lib/structured-data';

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
    expect(data.url).toBe('https://vpn.ozoxy.ru/ru-RU/help');
    expect(data.inLanguage).toBe('ru-RU');
    expect(data.mainEntity).toHaveLength(2);
    expect(data.mainEntity?.[0]).toMatchObject({
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
        item: 'https://vpn.ozoxy.ru/en-EN',
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'Docs',
        item: 'https://vpn.ozoxy.ru/en-EN/docs',
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
    expect(data.url).toBe('https://vpn.ozoxy.ru/en-EN/docs');
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
      url: 'https://vpn.ozoxy.ru/en-EN/pricing',
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
    expect(data.url).toBe('https://vpn.ozoxy.ru/en-EN/download');
    expect(data.downloadUrl).toBe('https://vpn.ozoxy.ru/en-EN/download');
    expect(data.featureList).toEqual([
      'Reality masking',
      '10 Gbps backbone',
      'Multi-platform access',
    ]);
    expect(data.offers).toMatchObject([
      {
        '@type': 'Offer',
        price: '0',
        url: 'https://vpn.ozoxy.ru/en-EN/pricing',
      },
    ]);
  });
});
