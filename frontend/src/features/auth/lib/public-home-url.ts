import { SITE_URL } from '@/shared/lib/seo-route-policy';
import { normalizeAuthLocale } from './redirect-path';

export function getPublicHomeHref(locale: string): string {
  return new URL(`/${normalizeAuthLocale(locale)}`, SITE_URL).toString();
}
