import type { MetadataRoute } from 'next'
import { locales } from '@/i18n/config'

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

const ROUTES = [
    '/dashboard',
    '/servers',
    '/users',
    '/analytics',
    '/monitoring',
    '/subscriptions',
    '/settings',
]

export default function sitemap(): MetadataRoute.Sitemap {
    const entries: MetadataRoute.Sitemap = []

    for (const locale of locales) {
        for (const route of ROUTES) {
            entries.push({
                url: `${BASE_URL}/${locale}${route}`,
                lastModified: new Date(),
                changeFrequency: 'daily',
                priority: route === '/dashboard' ? 1 : 0.8,
            })
        }
    }

    return entries
}
