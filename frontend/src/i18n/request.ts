import { getRequestConfig } from 'next-intl/server';
import { defaultLocale, locales } from './config';

type Locale = (typeof locales)[number];

// Helper for deep merging translation objects
function deepMerge(target: any, source: any) {
    for (const key in source) {
        if (source[key] instanceof Object && key in target) {
            Object.assign(source[key], deepMerge(target[key], source[key]));
        }
    }
    return { ...target, ...source };
}

export default getRequestConfig(async ({ locale }) => {
    const resolvedLocale: Locale = locales.includes(locale as Locale) ? (locale as Locale) : defaultLocale;

    // Load base messages (English) and current locale messages
    const baseMessages = await loadLocaleMessages(defaultLocale);
    let messages = baseMessages;

    if (resolvedLocale !== defaultLocale) {
        try {
            const currentMessages = await loadLocaleMessages(resolvedLocale);
            // Deep merge ensures that missing keys in current locale fall back to English
            messages = deepMerge(baseMessages, currentMessages);
        } catch (error) {
            console.error(`Failed to load messages for ${resolvedLocale}, falling back to ${defaultLocale}`, error);
        }
    }

    return {
        locale: resolvedLocale,
        messages
    };
});

async function loadLocaleMessages(locale: Locale) {
    const [
        header,
        navigation,
        dashboard,
        users,
        servers,
        placeholder,
        usersTable,
        serversTable,
        serverCard,
        landing,
        footer
    ] = await Promise.all([
        import(`../../messages/${locale}/header.json`),
        import(`../../messages/${locale}/navigation.json`),
        import(`../../messages/${locale}/dashboard.json`),
        import(`../../messages/${locale}/users.json`),
        import(`../../messages/${locale}/servers.json`),
        import(`../../messages/${locale}/placeholder.json`),
        import(`../../messages/${locale}/users-table.json`),
        import(`../../messages/${locale}/servers-table.json`),
        import(`../../messages/${locale}/server-card.json`),
        import(`../../messages/${locale}/landing.json`),
        import(`../../messages/${locale}/footer.json`)
    ]);

    return {
        Header: header.default,
        Navigation: navigation.default,
        Dashboard: dashboard.default,
        Users: users.default,
        Servers: servers.default,
        Placeholder: placeholder.default,
        UsersTable: usersTable.default,
        ServersTable: serversTable.default,
        ServerCard: serverCard.default,
        Landing: landing.default,
        Footer: footer.default
    };
}
