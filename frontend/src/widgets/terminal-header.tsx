import { Wifi } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { MobileSidebar } from '@/widgets/mobile-sidebar';
import { TerminalHeaderControls } from '@/widgets/terminal-header-controls';
import { TerminalHeaderPerformance } from '@/widgets/terminal-header-performance';

interface TerminalHeaderProps {
  performanceMode?: 'off' | 'idle' | 'always';
  showMobileSidebar?: boolean;
}

export async function TerminalHeader({
  performanceMode = 'idle',
  showMobileSidebar = false,
}: TerminalHeaderProps) {
  const headerT = await getTranslations('Header');
  const loginT = await getTranslations('Auth.login');
  const registerT = await getTranslations('Auth.register');

  return (
    <header className="sticky top-0 z-30 border-b border-grid-line/50 bg-terminal-surface/95 backdrop-blur-xl shadow-sm transition-all dark:shadow-none">
      <div className="flex h-16 w-full items-center gap-3 px-4 sm:px-5 md:px-6">
        {showMobileSidebar ? (
          <div className="md:hidden">
            <MobileSidebar />
          </div>
        ) : null}

        <div className="flex min-w-0 flex-1 items-center gap-3 md:gap-4">
          <TerminalHeaderPerformance
            mode={performanceMode}
            fpsLabel={headerT('fps')}
            pingLabel={headerT('ping')}
          />

          <div className="flex items-center gap-2 rounded-full border border-matrix-green/30 bg-matrix-green/10 px-3 py-1 text-xs font-mono text-matrix-green">
            <Wifi className="h-3 w-3 animate-pulse" />
            <span className="hidden md:inline">{headerT('netUplink')}</span>
          </div>
        </div>

        <TerminalHeaderControls
          loginLabel={loginT('submitButton')}
          registerLabel={registerT('submitButton')}
        />
      </div>
    </header>
  );
}
