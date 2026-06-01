'use client';

import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { ArrowUpRight, Gift, Ticket } from 'lucide-react';
import {
  areCheckoutCodeDiscountsEnabled,
  areGiftCodesEnabled,
  areInviteCodesEnabled,
  arePromoCodesEnabled,
  isGrowthHubEnabled,
  isReferralProgramEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';

export function CodesSection() {
  const t = useTranslations('Subscriptions');
  const { data: capabilities } = useClientCapabilities();
  const rewardsHubVisible =
    isGrowthHubEnabled(capabilities) ||
    areInviteCodesEnabled(capabilities) ||
    isReferralProgramEnabled(capabilities) ||
    areGiftCodesEnabled(capabilities);
  const checkoutCodesVisible =
    arePromoCodesEnabled(capabilities) ||
    areCheckoutCodeDiscountsEnabled(capabilities);

  if (!rewardsHubVisible && !checkoutCodesVisible) {
    return null;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
      {rewardsHubVisible ? (
        <div className="cyber-card p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-xl border border-neon-purple/30 bg-neon-purple/10 p-3">
              <Gift className="h-6 w-6 text-neon-purple" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-display text-neon-purple">
                {t('rewardsHubTitle')}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('rewardsHubDescription')}
              </p>
            </div>
          </div>

          <div className="mt-6">
            <Link
              href="/rewards"
              className="inline-flex items-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-3 text-sm font-mono text-neon-cyan transition-colors hover:bg-neon-cyan/20"
            >
              {t('rewardsHubCta')}
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      ) : null}

      {checkoutCodesVisible ? (
        <div className="cyber-card p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 p-3">
              <Ticket className="h-6 w-6 text-neon-cyan" />
            </div>
            <div>
              <h3 className="text-lg font-display text-neon-cyan">
                {t('checkoutCodesTitle')}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('checkoutCodesDescription')}
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
