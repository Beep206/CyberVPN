import { LockKeyhole } from 'lucide-react';
import { STAGE1_GROWTH_HUB_UI_ENABLED } from '@/shared/lib/stage1-growth-flags';
import { ReferralCabinetDashboard } from '@/widgets/referral-cabinet/referral-cabinet-dashboard';

export default function ReferralPage() {
  if (!STAGE1_GROWTH_HUB_UI_ENABLED) {
    return (
      <div className="mx-auto w-full max-w-3xl">
        <div className="cyber-card p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 p-3">
              <LockKeyhole className="h-5 w-5 text-neon-cyan" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs font-mono uppercase tracking-[0.2em] text-neon-cyan">
                S1 beta
              </p>
              <h1 className="mt-2 text-xl font-display text-white">
                Rewards hub is paused
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Public referral, gift, and promo-code flows are disabled during the controlled public beta.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl">
      <ReferralCabinetDashboard />
    </div>
  );
}
