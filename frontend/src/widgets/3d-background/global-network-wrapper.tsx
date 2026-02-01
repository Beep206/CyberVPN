'use client';

import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { ErrorBoundary } from "@/shared/ui/error-boundary";

const GlobalNetworkScene = dynamic(() => import("@/3d/scenes/GlobalNetwork"), {
    ssr: false,
});

export function GlobalNetworkWrapper() {
    const pathname = usePathname();

    return (
        <ErrorBoundary fallback={<div className="w-full h-full bg-terminal-bg flex items-center justify-center text-xs text-muted-foreground">3D Background Disabled (Extension Conflict)</div>}>
            <GlobalNetworkScene key={pathname} />
        </ErrorBoundary>
    );
}
