export const MONITORING_TOPIC_OPTIONS = [
  'servers',
  'payments',
  'general',
  'users',
  'system',
] as const;

export type MonitoringTopic = (typeof MONITORING_TOPIC_OPTIONS)[number];

function appendApiVersionPath(url: URL) {
  const normalizedPath = url.pathname.replace(/\/$/, '');
  url.pathname = normalizedPath.endsWith('/api/v1')
    ? normalizedPath
    : `${normalizedPath}/api/v1`;
}

export function resolveRealtimeBaseUrl() {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  const fallbackOrigin =
    typeof window !== 'undefined' ? window.location.origin : '';
  const rawBaseUrl = configuredBaseUrl || fallbackOrigin;

  if (!rawBaseUrl) {
    return '';
  }

  const url = new URL(rawBaseUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  appendApiVersionPath(url);
  url.search = '';
  url.hash = '';

  return url.toString().replace(/\/$/, '');
}

export function buildMonitoringSocketUrl(ticket: string) {
  const baseUrl = resolveRealtimeBaseUrl();
  if (!baseUrl) {
    throw new Error('Realtime base URL is not configured.');
  }

  const socketUrl = new URL(`${baseUrl}/ws/monitoring`);
  socketUrl.searchParams.set('ticket', ticket);
  return socketUrl.toString();
}
