import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/dashboard/', '/miniapp/'],
      },
    ],
    sitemap: 'https://vpn-admin.example.com/sitemap.xml',
  };
}
