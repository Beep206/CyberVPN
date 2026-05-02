import type { PublicNetworkRegion } from '@/lib/api/public-network';

export function pollingInterval(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) return false;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
    return intervalMs;
  };
}

export function formatCount(value: number | null | undefined, locale: string) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat(locale).format(value);
}

export function formatTraffic(bytes: number | null | undefined, locale: string) {
  if (typeof bytes !== 'number') return '—';
  if ((bytes ?? 0) <= 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let size = bytes ?? 0;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  const maximumFractionDigits = size >= 100 ? 0 : size >= 10 ? 1 : 2;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits }).format(size)} ${units[unitIndex]}`;
}

export function formatAvailability(value: number | null | undefined, locale: string) {
  if (typeof value !== 'number') return '—';
  return `${new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)}%`;
}

export function resolveCountryLabel(countryCode: string, locale: string) {
  if (!countryCode || countryCode.toLowerCase() === 'unknown') {
    return 'UNKNOWN';
  }

  try {
    const displayNames = new Intl.DisplayNames([locale.split('-')[0], 'en'], { type: 'region' });
    return displayNames.of(countryCode.toUpperCase()) ?? countryCode.toUpperCase();
  } catch {
    return countryCode.toUpperCase();
  }
}

const COUNTRY_COORDINATES: Record<string, { lat: number; lng: number }> = {
  AU: { lat: -33.8688, lng: 151.2093 },
  BR: { lat: -23.5505, lng: -46.6333 },
  CA: { lat: 43.6532, lng: -79.3832 },
  DE: { lat: 52.52, lng: 13.405 },
  FR: { lat: 48.8566, lng: 2.3522 },
  GB: { lat: 51.5074, lng: -0.1278 },
  IN: { lat: 28.6139, lng: 77.209 },
  JP: { lat: 35.6762, lng: 139.6503 },
  NL: { lat: 52.3676, lng: 4.9041 },
  RU: { lat: 55.7558, lng: 37.6173 },
  SG: { lat: 1.3521, lng: 103.8198 },
  TR: { lat: 41.0082, lng: 28.9784 },
  US: { lat: 40.7128, lng: -74.006 },
};

export function buildSceneServers(regions: PublicNetworkRegion[], locale: string) {
  return regions
    .map((region) => {
      const coordinates = COUNTRY_COORDINATES[region.countryCode.toUpperCase()];
      if (!coordinates) return null;

      return {
        id: region.id,
        name: resolveCountryLabel(region.countryCode, locale),
        lat: coordinates.lat,
        lng: coordinates.lng,
        status: region.status === 'degraded'
          ? 'warning'
          : region.status === 'offline'
            ? 'offline'
            : 'online',
      } as const;
    })
    .filter((region): region is NonNullable<typeof region> => Boolean(region));
}

export function buildSceneConnections(
  sceneServers: Array<{ lat: number; lng: number }>,
) {
  if (sceneServers.length < 2) return [];

  const anchor = sceneServers[0];
  return sceneServers.slice(1).map((server) => ({
    from: { lat: anchor.lat, lng: anchor.lng },
    to: { lat: server.lat, lng: server.lng },
  }));
}
