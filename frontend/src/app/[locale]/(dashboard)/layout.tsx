import { CyberSidebar } from "@/widgets/cyber-sidebar";
import { MobileSidebar } from "@/widgets/mobile-sidebar";
import { TerminalHeader } from "@/widgets/terminal-header";
import { GlobalNetworkWrapper } from "@/widgets/3d-background/global-network-wrapper";
import { Scanlines } from "@/shared/ui/atoms/scanlines";
import { AuthGuard } from "@/features/auth/components";
import { ErrorBoundary } from "@/shared/ui/error-boundary";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <AuthGuard>
            <div className="flex h-screen w-full overflow-hidden bg-terminal-bg text-foreground">
                {/* Skip to main content link for keyboard/screen reader users */}
                <a
                    href="#main-content"
                    className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-neon-cyan focus:text-black focus:px-4 focus:py-2 focus:rounded-sm focus:font-mono focus:text-sm"
                >
                    Skip to main content
                </a>
                <Scanlines />
                <ErrorBoundary label="Sidebar">
                    <CyberSidebar />
                </ErrorBoundary>
                <MobileSidebar />
                <div className="relative flex flex-1 flex-col overflow-hidden md:pl-64">
                    <ErrorBoundary label="Header">
                        <TerminalHeader />
                    </ErrorBoundary>
                    <main id="main-content" tabIndex={-1} aria-live="polite" className="flex-1 overflow-y-auto overflow-x-hidden relative p-4 md:p-6 pb-20 z-10 focus:outline-hidden">
                        {children}
                    </main>

                    {/* 3D Background - Fixed behind content */}
                    <div className="fixed inset-0 z-0 pointer-events-none md:pl-64">
                        <GlobalNetworkWrapper />
                    </div>

                    {/* Gradient Overlay to ensure text readability over 3D background */}
                    <div className="fixed inset-0 z-0 pointer-events-none bg-gradient-to-br from-terminal-bg/90 via-terminal-bg/80 to-terminal-bg/40 md:pl-64" />
                </div>
            </div>
        </AuthGuard>
    );
}
