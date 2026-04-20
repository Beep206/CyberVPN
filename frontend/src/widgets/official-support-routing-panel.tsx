import { Link } from '@/i18n/navigation';
import { getOfficialSupportProfile } from '@/shared/lib/official-support-routing';

export function OfficialSupportRoutingPanel({ locale }: { locale: string }) {
  const profile = getOfficialSupportProfile();

  return (
    <section className="rounded-[1.75rem] border border-grid-line/20 bg-terminal-surface/45 p-6 shadow-[0_0_32px_rgba(0,255,255,0.05)] backdrop-blur md:p-8">
      <div className="grid gap-4 md:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-[1.25rem] border border-grid-line/20 bg-terminal-bg/60 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
            Official support routing
          </p>
          <h2 className="mt-3 font-display text-2xl uppercase tracking-[0.12em] text-foreground">
            {profile.supportLabel}
          </h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{profile.supportEmail}</p>
            <p>Response window: {profile.responseWindow}</p>
            <p>Surface: {profile.surfaceLabel}</p>
          </div>
        </article>

        <article className="rounded-[1.25rem] border border-grid-line/20 bg-terminal-bg/60 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-purple/80">
            Communication and legal context
          </p>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{profile.communicationSenderName}</p>
            <p>{profile.communicationSenderEmail}</p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href={profile.helpCenterPath} locale={locale} className="text-neon-cyan underline underline-offset-4">
                Help center
              </Link>
              <Link href={profile.legalPaths.terms} locale={locale} className="text-neon-purple underline underline-offset-4">
                Terms
              </Link>
              <Link href={profile.legalPaths.privacy} locale={locale} className="text-matrix-green underline underline-offset-4">
                Privacy
              </Link>
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}
