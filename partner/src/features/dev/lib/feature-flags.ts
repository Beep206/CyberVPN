import { useState, useEffect } from 'react';

// Define the available feature flags here
export const FEATURE_FLAGS = {
    enableCryptoPayments: {
        id: 'enableCryptoPayments',
        label: 'Enable Crypto Payments',
        description: 'Shows alternative payment methods in billing.',
        defaultState: false,
    },
    useMockData: {
        id: 'useMockData',
        label: 'Use Mock Data',
        description: 'Bypass API and use static mock data for servers.',
        defaultState: false,
    },
    newServerGrid: {
        id: 'newServerGrid',
        label: 'New Server Grid UI',
        description: 'Toggle the experimental grid layout for servers.',
        defaultState: false,
    },
    experimentalAnimations: {
        id: 'experimentalAnimations',
        label: 'Experimental Animations',
        description: 'Enable heavy WebGL/Framer animations.',
        defaultState: false,
    }
} as const;

export type FeatureFlagId = keyof typeof FEATURE_FLAGS;

class FeatureFlagManager {
    private flags: Record<FeatureFlagId, boolean>;
    private listeners: Set<(flags: Record<FeatureFlagId, boolean>) => void> = new Set();
    private readonly STORAGE_KEY = 'DEV_FEATURE_FLAGS';

    constructor() {
        // Initialize with default states
        const initialStates = Object.entries(FEATURE_FLAGS).reduce((acc, [key, flag]) => {
            acc[key as FeatureFlagId] = flag.defaultState;
            return acc;
        }, {} as Record<FeatureFlagId, boolean>);
        
        this.flags = initialStates;
    }

    // Load from localStorage (only in browser)
    load() {
        if (typeof window === 'undefined') return;
        try {
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                this.flags = { ...this.flags, ...parsed };
                this.notify();
            }
        } catch { /* ignore */ }
    }

    getFlags() {
        return this.flags;
    }

    getFlag(id: FeatureFlagId): boolean {
        return this.flags[id];
    }

    setFlag(id: FeatureFlagId, value: boolean) {
        this.flags = { ...this.flags, [id]: value };
        this.save();
        this.notify();
    }

    reset() {
        const initialStates = Object.entries(FEATURE_FLAGS).reduce((acc, [key, flag]) => {
            acc[key as FeatureFlagId] = flag.defaultState;
            return acc;
        }, {} as Record<FeatureFlagId, boolean>);
        this.flags = initialStates;
        this.save();
        this.notify();
    }

    subscribe(listener: (flags: Record<FeatureFlagId, boolean>) => void) {
        this.listeners.add(listener);
        listener(this.flags);
        return () => { this.listeners.delete(listener); };
    }

    private save() {
        if (typeof window !== 'undefined') {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.flags));
        }
    }

    private notify() {
        this.listeners.forEach(l => l(this.flags));
    }
}

export const featureFlagManager = new FeatureFlagManager();

// Initialize immediately if in browser
if (typeof window !== 'undefined') {
    featureFlagManager.load();
}

/**
 * React hook to consume feature flags
 */
export function useFeatureFlags() {
    const [flags, setFlags] = useState<Record<FeatureFlagId, boolean>>(featureFlagManager.getFlags());

    useEffect(() => {
        return featureFlagManager.subscribe(setFlags);
    }, []);

    const toggleFlag = (id: FeatureFlagId) => {
        featureFlagManager.setFlag(id, !flags[id]);
    };

    const resetFlags = () => {
        featureFlagManager.reset();
    };

    return { flags, toggleFlag, resetFlags };
}
