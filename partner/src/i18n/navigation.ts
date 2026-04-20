import { createNavigation } from 'next-intl/navigation';
import { defaultLocale, locales } from './config';

export const {
    Link,
    usePathname,
    useRouter,
    redirect,
    permanentRedirect,
    getPathname
} = createNavigation({
    locales,
    defaultLocale,
    localePrefix: 'always'
});
