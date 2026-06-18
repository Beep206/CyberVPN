export const TELEGRAM_ACCOUNT_LINK_STORAGE_KEY = 'telegram_account_link_session';

export interface TelegramAccountLinkSession {
  token: string;
  botUrl: string;
  deepLinkUrl?: string;
  requestedAt: number;
}

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

export function saveTelegramAccountLinkSession(session: TelegramAccountLinkSession): void {
  if (!isBrowser()) return;

  window.sessionStorage.setItem(
    TELEGRAM_ACCOUNT_LINK_STORAGE_KEY,
    JSON.stringify(session),
  );
}

export function readTelegramAccountLinkSession(): TelegramAccountLinkSession | null {
  if (!isBrowser()) return null;

  const raw = window.sessionStorage.getItem(TELEGRAM_ACCOUNT_LINK_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<TelegramAccountLinkSession>;
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

export function clearTelegramAccountLinkSession(): void {
  if (!isBrowser()) return;
  window.sessionStorage.removeItem(TELEGRAM_ACCOUNT_LINK_STORAGE_KEY);
}
