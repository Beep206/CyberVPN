import { Suspense } from "react";
import { CyberSidebar } from "@/widgets/cyber-sidebar";
import { MobileSidebar } from "@/widgets/mobile-sidebar";
import { TerminalHeader } from "@/widgets/terminal-header";
import { GlobalNetworkWrapper } from "@/widgets/3d-background/global-network-wrapper";
import { Scanlines } from "@/shared/ui/atoms/scanlines";
import DashboardLoading from "./loading";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex h-screen w-full overflow-hidden bg-terminal-bg text-foreground">
            <Scanlines />
            <CyberSidebar />
            <MobileSidebar />
            <div className="relative flex flex-1 flex-col overflow-hidden md:pl-64">
                <TerminalHeader />
                <main className="flex-1 overflow-y-auto overflow-x-hidden relative p-4 md:p-6 pb-20 z-10">
                    <Suspense fallback={<DashboardLoading />}>
                        {children}
                    </Suspense>
                </main>

                {/* 3D Background - Fixed behind content */}
                <div className="fixed inset-0 z-0 pointer-events-none md:pl-64">
                    <GlobalNetworkWrapper />
                </div>

                {/* Gradient Overlay to ensure text readability over 3D background */}
                <div className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-terminal-bg/90 via-terminal-bg/80 to-terminal-bg/40 md:pl-64" />
            </div>
        </div>
    );
}
