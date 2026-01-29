'use client';

import dynamic from "next/dynamic";
import { ErrorBoundary } from "@/shared/ui/error-boundary";

const GlobalNetworkScene = dynamic(() => import("@/3d/scenes/GlobalNetwork"), {
    ssr: false,
});

export function GlobalNetworkWrapper() {
    return (
        <ErrorBoundary fallback={<div className="w-full h-full bg-terminal-bg" />}>
            <GlobalNetworkScene />
        </ErrorBoundary>
    );
}
