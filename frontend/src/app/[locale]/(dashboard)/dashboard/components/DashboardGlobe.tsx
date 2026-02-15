'use client';

import dynamic from "next/dynamic";
import { useEffect, useState } from 'react';
import { ErrorBoundary } from "@/shared/ui/error-boundary";

const GlobalNetworkScene = dynamic(() => import("@/3d/scenes/GlobalNetwork"), {
    ssr: false,
    loading: () => null,
});

const MIN_CPU_CORES = 8;
const MIN_DEVICE_MEMORY_GB = 4;
const MIN_VIEWPORT_WIDTH = 1024;
const IDLE_TIMEOUT_MS = 1_500;

interface NavigatorConnectionLike {
    saveData?: boolean;
    effectiveType?: string;
}

interface NavigatorWithPerformanceHints extends Navigator {
    deviceMemory?: number;
    connection?: NavigatorConnectionLike;
}

function shouldRender3DGlobe(): boolean {
    if (typeof window === 'undefined') return false;

    const nav = navigator as NavigatorWithPerformanceHints;
    const hasEnoughCores = (nav.hardwareConcurrency ?? 0) >= MIN_CPU_CORES;
    const hasEnoughMemory = (nav.deviceMemory ?? 0) >= MIN_DEVICE_MEMORY_GB;
    const saveDataEnabled = nav.connection?.saveData ?? false;
    const lowBandwidth = ['slow-2g', '2g'].includes(nav.connection?.effectiveType ?? '');
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isNarrowViewport = window.innerWidth < MIN_VIEWPORT_WIDTH;

    return (
        hasEnoughCores
        && hasEnoughMemory
        && !saveDataEnabled
        && !lowBandwidth
        && !prefersReducedMotion
        && !isNarrowViewport
    );
}

export function DashboardGlobe() {
    const [showGlobe, setShowGlobe] = useState(false);

    useEffect(() => {
        const win = window as Window & {
            requestIdleCallback?: (callback: () => void, options?: { timeout: number }) => number;
            cancelIdleCallback?: (handle: number) => void;
        };

        const runCheck = () => {
            setShowGlobe(shouldRender3DGlobe());
        };

        if (win.requestIdleCallback) {
            const handle = win.requestIdleCallback(runCheck, { timeout: IDLE_TIMEOUT_MS });
            return () => {
                win.cancelIdleCallback?.(handle);
            };
        }

        const timeoutId = window.setTimeout(runCheck, 200);
        return () => window.clearTimeout(timeoutId);
    }, []);

    return (
        <>
            {/* 3D Background - Fixed behind content */}
            <div className="fixed inset-0 z-0 pointer-events-none md:pl-64">
                {showGlobe ? (
                    <ErrorBoundary label="3D Globe" fallback={null}>
                        <GlobalNetworkScene />
                    </ErrorBoundary>
                ) : null}
            </div>

            {/* Gradient Overlay to ensure text readability over 3D background */}
            <div className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-terminal-bg/90 via-terminal-bg/80 to-terminal-bg/40 md:pl-64" />
        </>
    );
}
