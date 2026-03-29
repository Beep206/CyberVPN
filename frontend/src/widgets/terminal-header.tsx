import { Menu, Wifi } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { TerminalHeaderControls } from '@/widgets/terminal-header-controls';
import { TerminalHeaderPerformance } from '@/widgets/terminal-header-performance';

interface TerminalHeaderProps {
  performanceMode?: 'off' | 'idle' | 'always';
}

export async function TerminalHeader({ performanceMode = 'idle' }: TerminalHeaderProps) {
  const headerT = await getTranslations('Header');
  const loginT = await getTranslations('Auth.login');
  const registerT = await getTranslations('Auth.register');

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center gap-4 bg-terminal-surface/95 backdrop-blur-xl border-b border-grid-line/50 shadow-sm dark:shadow-none px-6 pl-20 md:pl-6 transition-all">
      <div className="flex flex-1 items-center gap-4">
        <MagneticButton strength={15}>
          <div
            aria-hidden="true"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-grid-line/30 bg-muted/50 text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          >
            <Menu className="h-4 w-4" />
          </div>
        </MagneticButton>

        <TerminalHeaderPerformance mode={performanceMode} fpsLabel={headerT('fps')} pingLabel={headerT('ping')} />

        <div className="flex items-center gap-2 text-xs font-mono text-matrix-green bg-matrix-green/10 px-3 py-1 rounded-full border border-matrix-green/30">
          <Wifi className="h-3 w-3 animate-pulse" />
          <span className="hidden md:inline">{headerT('netUplink')}</span>
        </div>
      </div>

      <TerminalHeaderControls
        loginLabel={loginT('submitButton')}
        registerLabel={registerT('submitButton')}
      />
    </header>
  );
}
