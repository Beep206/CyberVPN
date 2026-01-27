import { getRequestConfig } from 'next-intl/server';
import { defaultLocale, locales } from './config';

type Locale = (typeof locales)[number];

export default getRequestConfig(async ({ requestLocale }) => {
    const locale = await requestLocale;
    const resolvedLocale: Locale = locales.includes(locale as Locale) ? (locale as Locale) : defaultLocale;

    return {
        locale: resolvedLocale,
        messages: (await import(`../../messages/${resolvedLocale}.json`)).default
    };
});
