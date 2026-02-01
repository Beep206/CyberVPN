"use cache"

import { cacheLife } from 'next/cache'

export async function getCachedServerStats() {
    cacheLife('minutes')
    // TODO: Replace with real API call
    return { totalServers: 4, onlineServers: 3, activeSessions: 1337 }
}
