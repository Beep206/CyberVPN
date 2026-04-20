export type UptimeStatus = 'nominal' | 'warning' | 'outage' | 'maintenance';

export interface UptimeDay {
    date: string;
    status: UptimeStatus;
}

const HISTORY_LENGTH = 90;

function resolveStatus(offset: number): UptimeStatus {
    if (offset % 41 === 0) return 'outage';
    if (offset % 23 === 0) return 'maintenance';
    if (offset % 17 === 0) return 'warning';
    return 'nominal';
}

export function buildUptimeHistorySnapshot(anchorDate: Date): UptimeDay[] {
    const data: UptimeDay[] = [];
    const startDate = new Date(Date.UTC(
        anchorDate.getUTCFullYear(),
        anchorDate.getUTCMonth(),
        anchorDate.getUTCDate(),
    ));

    for (let offset = HISTORY_LENGTH - 1; offset >= 0; offset -= 1) {
        const day = new Date(startDate);
        day.setUTCDate(startDate.getUTCDate() - offset);

        data.push({
            date: day.toISOString().split('T')[0],
            status: resolveStatus(offset),
        });
    }

    return data;
}
