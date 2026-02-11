import type { MetadataRoute } from 'next';
import { locales } from '@/i18n/config';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://vpn-admin.example.com';
  const lastModified = new Date();

  // Public pages that should be indexed
  const publicRoutes = ['/', '/login', '/register'];

  // Generate sitemap entries for all locales
  const sitemapEntries: MetadataRoute.Sitemap = [];

  for (const locale of locales) {
    for (const route of publicRoutes) {
      sitemapEntries.push({
        url: `${baseUrl}/${locale}${route}`,
        lastModified,
        changeFrequency: 'weekly',
        priority: route === '/' ? 1.0 : 0.8,
      });
    }
  }

  return sitemapEntries;
}
