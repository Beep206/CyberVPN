import { AxiosError } from 'axios';

export type MessagingChipTone = 'neutral' | 'success' | 'info' | 'warning' | 'danger';

export function shortMessagingId(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value.length <= 12 ? value : `${value.slice(0, 8)}...${value.slice(-4)}`;
}

export function humanizeMessagingToken(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function formatMessagingDateTime(value: string | null | undefined, locale: string) {
  if (!value) {
    return '--';
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function messagingStatusTone(status: string): MessagingChipTone {
  if (status === 'open') {
    return 'success';
  }
  if (status === 'closed' || status === 'archived') {
    return 'neutral';
  }
  if (status === 'locked') {
    return 'danger';
  }
  return 'info';
}

export function messagingPriorityTone(priority: string): MessagingChipTone {
  if (priority === 'urgent') {
    return 'danger';
  }
  if (priority === 'high') {
    return 'warning';
  }
  if (priority === 'normal') {
    return 'info';
  }
  return 'neutral';
}

export function messagingResponseStateTone(responseState: string): MessagingChipTone {
  if (responseState === 'waiting_admin') {
    return 'danger';
  }
  if (responseState === 'waiting_customer') {
    return 'warning';
  }
  return 'neutral';
}

export function messagingVisibilityTone(visibility: string): MessagingChipTone {
  return visibility === 'internal' ? 'warning' : 'info';
}

export function getMessagingErrorMessage(error: unknown, fallback: string) {
  if (error instanceof AxiosError) {
    const detail = error.response?.data;
    if (typeof detail === 'object' && detail !== null && 'detail' in detail) {
      const message = detail.detail;
      if (typeof message === 'string') {
        return message;
      }
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
