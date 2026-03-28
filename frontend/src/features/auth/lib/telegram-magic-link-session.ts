export const TELEGRAM_MAGIC_LINK_STORAGE_KEY = 'telegram_magic_link_session';

export interface TelegramMagicLinkSession {
  token: string;
  botUrl: string;
  deepLinkUrl?: string;
  requestedAt: number;
}

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

export function saveTelegramMagicLinkSession(session: TelegramMagicLinkSession): void {
  if (!isBrowser()) return;

  window.sessionStorage.setItem(
    TELEGRAM_MAGIC_LINK_STORAGE_KEY,
    JSON.stringify(session),
  );
}

export function readTelegramMagicLinkSession(): TelegramMagicLinkSession | null {
  if (!isBrowser()) return null;

  const raw = window.sessionStorage.getItem(TELEGRAM_MAGIC_LINK_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<TelegramMagicLinkSession>;
    if (
      typeof parsed.token !== 'string' ||
      typeof parsed.botUrl !== 'string' ||
      typeof parsed.requestedAt !== 'number'
    ) {
      return null;
    }

    return {
      token: parsed.token,
      botUrl: parsed.botUrl,
      deepLinkUrl: typeof parsed.deepLinkUrl === 'string' ? parsed.deepLinkUrl : undefined,
      requestedAt: parsed.requestedAt,
    };
  } catch {
    return null;
  }
}

export function clearTelegramMagicLinkSession(): void {
  if (!isBrowser()) return;
  window.sessionStorage.removeItem(TELEGRAM_MAGIC_LINK_STORAGE_KEY);
}
