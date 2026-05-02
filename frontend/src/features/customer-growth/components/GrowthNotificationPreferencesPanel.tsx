import type { GrowthNotificationPreferences } from '@/lib/api/growth-notifications';

type GrowthNotificationPreferenceKey = keyof GrowthNotificationPreferences;

const CATEGORY_ROWS: Array<{
  titleKey: string;
  inApp: GrowthNotificationPreferenceKey;
  email: GrowthNotificationPreferenceKey;
  telegram: GrowthNotificationPreferenceKey;
}> = [
  {
    titleKey: 'preferences.categories.invites',
    inApp: 'growth_in_app_invites',
    email: 'growth_email_invites',
    telegram: 'growth_telegram_invites',
  },
  {
    titleKey: 'preferences.categories.referralRewards',
    inApp: 'growth_in_app_referral_rewards',
    email: 'growth_email_referral_rewards',
    telegram: 'growth_telegram_referral_rewards',
  },
  {
    titleKey: 'preferences.categories.gifts',
    inApp: 'growth_in_app_gifts',
    email: 'growth_email_gifts',
    telegram: 'growth_telegram_gifts',
  },
  {
    titleKey: 'preferences.categories.adminUpdates',
    inApp: 'growth_in_app_admin_updates',
    email: 'growth_email_admin_updates',
    telegram: 'growth_telegram_admin_updates',
  },
];

interface GrowthNotificationPreferencesPanelProps {
  t: (key: string) => string;
  preferences?: GrowthNotificationPreferences;
  isLoading?: boolean;
  isSaving?: boolean;
  onToggle: (key: GrowthNotificationPreferenceKey, nextValue: boolean) => void;
  variant?: 'dashboard' | 'miniapp';
}

function ToggleButton({
  checked,
  disabled,
  label,
  onClick,
  variant,
}: {
  checked: boolean;
  disabled: boolean;
  label: string;
  onClick: () => void;
  variant: 'dashboard' | 'miniapp';
}) {
  const activeClass =
    variant === 'miniapp'
      ? 'border-neon-cyan bg-neon-cyan/20 text-neon-cyan'
      : 'border-matrix-green/40 bg-matrix-green/10 text-matrix-green';
  const inactiveClass =
    variant === 'miniapp'
      ? 'border-border/70 bg-transparent text-muted-foreground'
      : 'border-grid-line/40 bg-transparent text-muted-foreground';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={[
        'rounded-full border px-3 py-1 text-xs font-mono transition-colors',
        checked ? activeClass : inactiveClass,
        disabled ? 'cursor-not-allowed opacity-60' : 'hover:border-neon-cyan/60',
      ].join(' ')}
      aria-pressed={checked}
    >
      {label}
    </button>
  );
}

export function GrowthNotificationPreferencesPanel({
  t,
  preferences,
  isLoading = false,
  isSaving = false,
  onToggle,
  variant = 'dashboard',
}: GrowthNotificationPreferencesPanelProps) {
  const wrapperClass =
    variant === 'miniapp'
      ? 'rounded-lg border border-[var(--tg-hint-color,oklch(0.35_0.08_200))] bg-[var(--tg-bg-color,oklch(0.08_0.015_260))] p-4'
      : 'cyber-card p-6';

  return (
    <section id="growth-notification-preferences" className={wrapperClass}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-display text-white">{t('preferences.title')}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{t('preferences.subtitle')}</p>
        </div>
        {isSaving ? (
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan">
            {t('preferences.saving')}
          </span>
        ) : null}
      </div>

      <div className="mt-5 space-y-4">
        {CATEGORY_ROWS.map((row) => {
          const values = preferences ?? {
            growth_in_app_invites: true,
            growth_email_invites: false,
            growth_telegram_invites: true,
            growth_in_app_referral_rewards: true,
            growth_email_referral_rewards: true,
            growth_telegram_referral_rewards: true,
            growth_in_app_gifts: true,
            growth_email_gifts: true,
            growth_telegram_gifts: true,
            growth_in_app_admin_updates: true,
            growth_email_admin_updates: true,
            growth_telegram_admin_updates: true,
          };

          return (
            <div
              key={row.titleKey}
              className="rounded-2xl border border-grid-line/30 bg-white/[0.03] p-4"
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <p className="text-sm font-mono text-white">{t(row.titleKey)}</p>
                <div className="flex flex-wrap gap-2">
                  <ToggleButton
                    checked={values[row.inApp]}
                    disabled={isLoading || isSaving}
                    label={t('preferences.channels.inApp')}
                    onClick={() => onToggle(row.inApp, !values[row.inApp])}
                    variant={variant}
                  />
                  <ToggleButton
                    checked={values[row.email]}
                    disabled={isLoading || isSaving}
                    label={t('preferences.channels.email')}
                    onClick={() => onToggle(row.email, !values[row.email])}
                    variant={variant}
                  />
                  <ToggleButton
                    checked={values[row.telegram]}
                    disabled={isLoading || isSaving}
                    label={t('preferences.channels.telegram')}
                    onClick={() => onToggle(row.telegram, !values[row.telegram])}
                    variant={variant}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">{t('preferences.note')}</p>
    </section>
  );
}
