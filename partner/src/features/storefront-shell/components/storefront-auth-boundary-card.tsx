import { Link } from '@/i18n/navigation';
import { AuthFormCard } from '@/features/auth/components';

type StorefrontAuthBoundaryCardProps = {
  title: string;
  description: string;
  primaryCtaLabel: string;
  secondaryCtaLabel: string;
};

export function StorefrontAuthBoundaryCard({
  title,
  description,
  primaryCtaLabel,
  secondaryCtaLabel,
}: StorefrontAuthBoundaryCardProps) {
  return (
    <AuthFormCard title={title} subtitle={description}>
      <div className="space-y-4 text-center">
        <p className="text-sm font-mono text-muted-foreground">
          Customer checkout stays on the branded storefront surface. Partner-operator identity remains isolated on portal hosts.
        </p>
        <div className="flex flex-col gap-3">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg bg-neon-cyan px-4 py-3 font-mono text-sm font-bold text-black transition-colors hover:bg-neon-cyan/90"
          >
            {primaryCtaLabel}
          </Link>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-4 py-3 font-mono text-sm text-neon-cyan transition-colors hover:border-neon-cyan/40"
          >
            {secondaryCtaLabel}
          </Link>
        </div>
      </div>
    </AuthFormCard>
  );
}
