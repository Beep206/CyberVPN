const DEFAULT_INTL_LOCALE = 'en-US';

const ROUTING_TO_INTL_LOCALE: Record<string, string> = {
  'en-EN': DEFAULT_INTL_LOCALE,
};

export function toIntlLocale(locale: string | null | undefined): string {
  const normalized = locale?.trim();
  if (!normalized) {
    return DEFAULT_INTL_LOCALE;
  }

  const mapped = ROUTING_TO_INTL_LOCALE[normalized] ?? normalized;
  try {
    return Intl.getCanonicalLocales(mapped)[0] ?? DEFAULT_INTL_LOCALE;
  } catch {
    return DEFAULT_INTL_LOCALE;
  }
}
