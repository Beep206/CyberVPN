import { ReferralCabinetDashboard } from '@/widgets/referral-cabinet/referral-cabinet-dashboard';

export default function RewardsPage() {
  return (
    <div className="mx-auto w-full max-w-7xl">
      <ReferralCabinetDashboard view="overview" />
    </div>
  );
}
