import type {
  GrowthNotificationDeliveryDetail,
  GrowthNotificationDetail,
} from '@/lib/api/growth-notifications';
import { getOfficialSupportProfile } from '@/shared/lib/official-support-routing';

export type GrowthTroubleshootingSurface = 'dashboard' | 'miniapp';

export type GrowthNotificationActionLink = {
  href: string;
  external: boolean;
  labelKey: string;
  escalationChannel?: string;
  deliveryChannel?: string | null;
};

function getTelegramSupportUrl(): string {
  const username = (process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? 'CyberVPNBot')
    .trim()
    .replace(/^@/, '');
  return `https://t.me/${username}?start=support`;
}

function buildContactPath(referenceCode: string): string {
  const params = new URLSearchParams({
    source: 'growth-notification',
    reference: referenceCode,
  });
  return `/contact?${params.toString()}`;
}

function buildSupportEmailHref(subject: string, body: string): string {
  const profile = getOfficialSupportProfile();
  const params = new URLSearchParams({
    subject,
    body,
  });
  return `mailto:${profile.supportEmail}?${params.toString()}`;
}

export function getGrowthNotificationRepairLink(
  surface: GrowthTroubleshootingSurface,
  delivery: GrowthNotificationDeliveryDetail,
): GrowthNotificationActionLink | null {
  const target = delivery.repair_target;
  if (!target) {
    return null;
  }

  if (target.kind === 'notification_preferences') {
    return {
      href: '#growth-notification-preferences',
      external: false,
      labelKey: 'notifications.openPreferences',
      deliveryChannel: delivery.delivery_channel,
    };
  }

  if (target.kind === 'telegram_link') {
    return {
      href: '/settings#linked-accounts',
      external: false,
      labelKey: 'notifications.openTelegramLinking',
      deliveryChannel: delivery.delivery_channel,
    };
  }

  if (target.kind === 'profile_review') {
    return {
      href: surface === 'dashboard' ? '/settings#profile-contact' : '/miniapp/profile#profile-contact',
      external: false,
      labelKey: 'notifications.reviewProfile',
      deliveryChannel: delivery.delivery_channel,
    };
  }

  return null;
}

export function getGrowthNotificationSupportActionLink(
  surface: GrowthTroubleshootingSurface,
  detail: GrowthNotificationDetail,
): GrowthNotificationActionLink {
  const supportRequiredDelivery =
    detail.deliveries.find((item) => item.support_required) ?? detail.deliveries[0] ?? null;
  const deliveryChannel = supportRequiredDelivery?.delivery_channel ?? null;
  const escalationChannel = detail.support_handoff.suggested_escalation_channel;

  if (surface === 'miniapp' || escalationChannel === 'telegram_support') {
    return {
      href: getTelegramSupportUrl(),
      external: true,
      labelKey: 'notifications.openTelegramSupport',
      escalationChannel: 'telegram_support',
      deliveryChannel,
    };
  }

  if (escalationChannel === 'support_email') {
    return {
      href: buildSupportEmailHref(
        detail.support_handoff.contact_subject,
        detail.support_handoff.contact_body,
      ),
      external: true,
      labelKey: 'notifications.emailSupport',
      escalationChannel: 'support_email',
      deliveryChannel,
    };
  }

  return {
    href: buildContactPath(detail.support_handoff.reference_code),
    external: false,
    labelKey: 'notifications.openSupportTicket',
    escalationChannel: 'contact_form',
    deliveryChannel,
  };
}

export function getGrowthNotificationHelpCenterLink(): GrowthNotificationActionLink {
  return {
    href: getOfficialSupportProfile().helpCenterPath,
    external: false,
    labelKey: 'notifications.openHelpCenter',
  };
}
