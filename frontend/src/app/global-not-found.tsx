import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { RouteNotFound } from '@/shared/ui/route-not-found';
import './globals.css';

export const metadata = withSiteMetadata(
  {
    title: 'Page Not Found | CyberVPN',
    description: 'The requested route is unavailable or not exposed on this VPN control surface.',
  },
  {
    routeType: 'private',
  },
);

export default function GlobalNotFound() {
  return (
    <html lang="en-EN" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className="antialiased bg-terminal-bg text-foreground min-h-screen selection:bg-neon-cyan/30"
      >
        <div className="relative z-10 min-h-full w-full">
          <RouteNotFound />
        </div>
        <div className="pointer-events-none fixed inset-0 z-50 scanline opacity-20" />
      </body>
    </html>
  );
}
