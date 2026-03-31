import Link from 'next/link';
import { Download } from 'lucide-react';
import { LanguageSelector } from '@/features/language-selector';
import { ThemeToggle } from '@/features/theme-toggle';
import { cn } from '@/lib/utils';

interface PublicTerminalHeaderControlsProps {
  downloadLabel: string;
  loginLabel: string;
  registerLabel: string;
}

export function PublicTerminalHeaderControls({
  downloadLabel,
  loginLabel,
  registerLabel,
}: PublicTerminalHeaderControlsProps) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <LanguageSelector />
      </div>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      <Link
        href="/download"
        className="touch-target hidden items-center gap-2 rounded-lg border border-grid-line/30 bg-terminal-surface/30 px-3 text-sm font-medium text-muted-foreground transition-all hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 lg:inline-flex"
        data-seo-cta="download"
        data-seo-zone="public_header"
      >
        <Download className="h-4 w-4" />
        {downloadLabel}
      </Link>

      <div className="mx-1 hidden h-6 w-px bg-grid-line/30 lg:block" />

      <div className="flex items-center gap-2">
        <Link
          href="/login"
          className="touch-target hidden items-center justify-center whitespace-nowrap rounded-lg border border-transparent px-4 text-sm font-medium text-muted-foreground ring-offset-background transition-all hover:border-white/10 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 lg:inline-flex"
          data-seo-cta="login"
          data-seo-zone="public_header"
        >
          {loginLabel}
        </Link>
        <Link
          href="/register"
          className={cn(
            'touch-target inline-flex items-center justify-center whitespace-nowrap rounded-lg border border-neon-cyan/20 px-3 text-xs font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 sm:px-4 sm:text-sm',
            'bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan hover:text-black hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]',
          )}
          data-seo-cta="register"
          data-seo-zone="public_header"
        >
          {registerLabel}
        </Link>
      </div>
    </div>
  );
}
