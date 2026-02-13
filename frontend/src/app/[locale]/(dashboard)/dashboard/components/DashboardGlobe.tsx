'use client';

import dynamic from "next/dynamic";
import { ErrorBoundary } from "@/shared/ui/error-boundary";

const GlobalNetworkScene = dynamic(() => import("@/3d/scenes/GlobalNetwork"), {
    ssr: false,
    loading: () => null,
});

export function DashboardGlobe() {
    return (
        <>
            {/* 3D Background - Fixed behind content */}
            <div className="fixed inset-0 z-0 pointer-events-none md:pl-64">
                <ErrorBoundary label="3D Globe" fallback={null}>
                    <GlobalNetworkScene />
                </ErrorBoundary>
            </div>

            {/* Gradient Overlay to ensure text readability over 3D background */}
            <div className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-terminal-bg/90 via-terminal-bg/80 to-terminal-bg/40 md:pl-64" />
        </>
    );
}
