import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

// ---------------------------------------------------------------------------
// ProfileDashboardScreen
// ---------------------------------------------------------------------------

/// Profile dashboard displaying user header, subscription stats cards,
/// and quick action buttons.
///
/// Watches [profileProvider] and [subscriptionProvider] for reactive updates.
/// Supports pull-to-refresh to reload profile and subscription data.
class ProfileDashboardScreen extends ConsumerWidget {
  const ProfileDashboardScreen({super.key});

  // ---- Time-based greeting ------------------------------------------------

  /// Returns a greeting string based on the current hour.
  ///
  /// Morning: 05:00-11:59, Afternoon: 12:00-16:59, Evening: 17:00-04:59.
  static String _greeting(AppLocalizations l10n, [DateTime? now]) {
    final hour = (now ?? DateTime.now()).hour;
    if (hour >= 5 && hour < 12) return l10n.profileGreetingMorning;
    if (hour >= 12 && hour < 17) return l10n.profileGreetingAfternoon;
    return l10n.profileGreetingEvening;
  }

  // ---- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncProfile = ref.watch(profileProvider);
    final asyncSubscription = ref.watch(subscriptionProvider);

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: _greeting(l10n),
          style: Theme.of(context).appBarTheme.titleTextStyle,
        ),
      ),
      body: asyncProfile.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorBody(
          message: error.toString(),
          onRetry: () => ref.invalidate(profileProvider),
        ),
        data: (profileState) {
          final profile = profileState.profile;
          if (profile == null) {
            return Center(child: Text(l10n.profileNoProfileData));
          }

          final subState = asyncSubscription.value;

          return RefreshIndicator(
            onRefresh: () async {
              await Future.wait([
                ref.read(profileProvider.notifier).refreshProfile(),
                ref.read(subscriptionProvider.notifier).loadSubscription(),
              ]);
            },
            child: ListView(
              padding: const EdgeInsets.symmetric(
                horizontal: Spacing.md,
                vertical: Spacing.md,
              ),
              children: [
                // -- Profile header --
                _ProfileHeader(profile: profile),
                const SizedBox(height: Spacing.lg),

                // -- Stats cards --
                _StatsCardsGrid(
                  subscription: subState?.currentSubscription,
                  subState: subState,
                ),
                const SizedBox(height: Spacing.lg),

                // -- Quick actions --
                _QuickActionsSection(
                  hasSubscription: subState?.isActive ?? false,
                ),

                // Bottom padding for navigation bar clearance.
                SizedBox(height: Spacing.navBarClearance(context)),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Profile Header
// ---------------------------------------------------------------------------

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.profile});

  final Profile profile;

  /// Generate initials from username or email.
  String _initials() {
    final name = profile.username ?? profile.email;
    final parts = name.split(RegExp(r'[\s@.]+'));
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : '?';
  }

  String _memberSince(AppLocalizations l10n) {
    final date = profile.createdAt;
    if (date == null) return '';
    return l10n.profileMemberSince(DateFormat.yMMMM().format(date));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Column(
      children: [
        // Avatar
        CircleAvatar(
          radius: 40,
          backgroundColor: colorScheme.primary.withAlpha(40),
          child: Text(
            _initials(),
            style: theme.textTheme.headlineMedium?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: Spacing.sm),

        // Username
        Text(
          profile.username ?? profile.email.split('@').first,
          style: theme.textTheme.titleLarge,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: Spacing.xs),

        // Email
        Text(
          profile.email,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),

        // Member since
        if (profile.createdAt != null) ...[
          const SizedBox(height: Spacing.xs),
          Text(
            _memberSince(l10n),
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Stats Cards Grid
// ---------------------------------------------------------------------------

class _StatsCardsGrid extends StatelessWidget {
  const _StatsCardsGrid({
    this.subscription,
    this.subState,
  });

  final SubscriptionEntity? subscription;
  final SubscriptionState? subState;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final sub = subscription;
    final daysRemaining = subState?.daysRemaining ?? 0;
    final totalDays = sub != null
        ? sub.endDate.difference(sub.startDate).inDays
        : 1;
    final daysProgress = totalDays > 0
        ? (daysRemaining / totalDays).clamp(0.0, 1.0)
        : 0.0;

    final trafficUsedGb = sub != null
        ? sub.trafficUsedBytes / (1024 * 1024 * 1024)
        : 0.0;
    final trafficLimitGb = sub != null
        ? sub.trafficLimitBytes / (1024 * 1024 * 1024)
        : 0.0;
    final trafficRatio = subState?.trafficUsageRatio ?? 0.0;

    final cards = <Widget>[
      // Card 1: Current Plan
      _StatsCard(
        key: const Key('stats_plan'),
        icon: Icons.workspace_premium_outlined,
        label: l10n.currentPlan,
        value: sub != null ? _statusLabel(sub.status, l10n) : l10n.profileStatsNoPlan,
        accentColor: sub != null
            ? _statusColor(sub.status)
            : null,
      ),

      // Card 2: Traffic Usage
      _StatsCard(
        key: const Key('stats_traffic'),
        icon: Icons.data_usage_outlined,
        label: l10n.profileStatsTraffic,
        value: trafficLimitGb > 0
            ? '${trafficUsedGb.toStringAsFixed(1)} / ${trafficLimitGb.toStringAsFixed(0)} GB'
            : l10n.profileStatsUnlimited,
        progress: trafficLimitGb > 0 ? trafficRatio : null,
        accentColor: _trafficColor(trafficRatio),
      ),

      // Card 3: Days Remaining
      _StatsCard(
        key: const Key('stats_days'),
        icon: Icons.calendar_today_outlined,
        label: l10n.profileStatsDaysLeft,
        value: sub != null ? '$daysRemaining' : '--',
        progress: sub != null ? daysProgress : null,
      ),

      // Card 4: Devices
      _StatsCard(
        key: const Key('stats_devices'),
        icon: Icons.devices_outlined,
        label: l10n.profileStatsDevices,
        value: sub != null
            ? '${sub.devicesConnected} / ${sub.maxDevices}'
            : '--',
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final cardWidth = (constraints.maxWidth - Spacing.sm) / 2;
        return Wrap(
          spacing: Spacing.sm,
          runSpacing: Spacing.sm,
          children: cards.map((card) {
            return SizedBox(
              width: cardWidth,
              child: card,
            );
          }).toList(),
        );
      },
    );
  }

  String _statusLabel(SubscriptionStatus status, AppLocalizations l10n) {
    return switch (status) {
      SubscriptionStatus.active => l10n.profileSubActive,
      SubscriptionStatus.trial => l10n.profileSubTrial,
      SubscriptionStatus.expired => l10n.profileSubExpired,
      SubscriptionStatus.cancelled => l10n.profileSubCancelled,
      SubscriptionStatus.pending => l10n.profileSubPending,
    };
  }

  Color _statusColor(SubscriptionStatus status) {
    return switch (status) {
      SubscriptionStatus.active => CyberColors.matrixGreen,
      SubscriptionStatus.trial => CyberColors.neonCyan,
      SubscriptionStatus.expired => const Color(0xFFFF5252),
      SubscriptionStatus.cancelled => const Color(0xFFFF5252),
      SubscriptionStatus.pending => const Color(0xFFFFAB40),
    };
  }

  Color _trafficColor(double ratio) {
    if (ratio < 0.5) return CyberColors.matrixGreen;
    if (ratio < 0.8) return const Color(0xFFFFAB40);
    return const Color(0xFFFF5252);
  }
}

// ---------------------------------------------------------------------------
// Stats Card
// ---------------------------------------------------------------------------

class _StatsCard extends StatelessWidget {
  const _StatsCard({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    this.progress,
    this.accentColor,
  });

  final IconData icon;
  final String label;
  final String value;
  final double? progress;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final accent = accentColor ?? colorScheme.primary;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icon row
            Container(
              padding: const EdgeInsets.all(Spacing.sm),
              decoration: BoxDecoration(
                color: accent.withAlpha(25),
                borderRadius: BorderRadius.circular(Radii.sm),
              ),
              child: Icon(icon, size: 20, color: accent),
            ),
            const SizedBox(height: Spacing.sm),

            // Label
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: Spacing.xs),

            // Value
            Text(
              value,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),

            // Optional progress bar
            if (progress != null) ...[
              const SizedBox(height: Spacing.sm),
              ClipRRect(
                borderRadius: BorderRadius.circular(Radii.sm),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 4,
                  backgroundColor: colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation<Color>(accent),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Quick Actions Section
// ---------------------------------------------------------------------------

class _QuickActionsSection extends StatelessWidget {
  const _QuickActionsSection({required this.hasSubscription});

  final bool hasSubscription;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileQuickActions,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),

        // Upgrade Plan
        _QuickActionButton(
          key: const Key('action_upgrade'),
          icon: Icons.rocket_launch_outlined,
          label: l10n.upgradePlan,
          onTap: () {
            unawaited(HapticFeedback.lightImpact());
            unawaited(context.push('/subscribe'));
          },
        ),

        // Invite Friends
        _QuickActionButton(
          key: const Key('action_invite'),
          icon: Icons.people_outline,
          label: l10n.profileInviteFriends,
          onTap: () {
            unawaited(HapticFeedback.lightImpact());
            unawaited(context.push('/referral'));
          },
        ),

        // Security Settings
        _QuickActionButton(
          key: const Key('action_security'),
          icon: Icons.security_outlined,
          label: l10n.profileSecuritySettings,
          onTap: () {
            unawaited(HapticFeedback.lightImpact());
            unawaited(context.push('/profile/2fa'));
          },
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Quick Action Button
// ---------------------------------------------------------------------------

class _QuickActionButton extends StatelessWidget {
  const _QuickActionButton({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.sm),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(Radii.md),
          child: Ink(
            decoration: BoxDecoration(
              border: Border.all(
                color: colorScheme.primary.withAlpha(40),
              ),
              borderRadius: BorderRadius.circular(Radii.md),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.md,
            ),
            child: Row(
              children: [
                Icon(icon, color: colorScheme.primary),
                const SizedBox(width: Spacing.md),
                Expanded(
                  child: Text(
                    label,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                Icon(
                  Icons.chevron_right,
                  color: colorScheme.onSurfaceVariant,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error Body
// ---------------------------------------------------------------------------

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: Spacing.md),
            Text(
              message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: Spacing.md),
              FilledButton.tonal(
                onPressed: onRetry,
                child: Text(l10n.retry),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
