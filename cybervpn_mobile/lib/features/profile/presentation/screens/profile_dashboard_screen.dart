import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart' hide TextDirection;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/cancel_subscription_sheet.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';
import 'package:cybervpn_mobile/shared/widgets/responsive_layout.dart';
import 'package:cybervpn_mobile/shared/widgets/staggered_list_item.dart';

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
              // Trigger medium haptic on pull-to-refresh threshold.
              final haptics = ref.read(hapticServiceProvider);
              unawaited(haptics.impact());

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
                  subscription: subState?.currentSubscription,
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

    final displayName = profile.username ?? profile.email.split('@').first;
    final memberSinceText = profile.createdAt != null ? ', ${_memberSince(l10n)}' : '';

    return Semantics(
      label: '$displayName, ${profile.email}$memberSinceText',
      hint: 'Your profile information',
      readOnly: true,
      child: Column(
        children: [
          // Avatar
          ExcludeSemantics(
            child: CircleAvatar(
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
          ),
          const SizedBox(height: Spacing.sm),

          // Username
          ExcludeSemantics(
            child: Text(
              displayName,
              style: theme.textTheme.titleLarge,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: Spacing.xs),

          // Email
          ExcludeSemantics(
            child: Text(
              profile.email,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),

          // Member since
          if (profile.createdAt != null) ...[
            const SizedBox(height: Spacing.xs),
            ExcludeSemantics(
              child: Text(
                _memberSince(l10n),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      ),
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

    // If no subscription, show "Get Started" CTA card instead of empty stats
    if (sub == null) {
      return const _NoSubscriptionCard(key: Key('no_subscription_card'));
    }

    final daysRemaining = subState?.daysRemaining ?? 0;
    final totalDays = sub.endDate.difference(sub.startDate).inDays;
    final daysProgress = totalDays > 0
        ? (daysRemaining / totalDays).clamp(0.0, 1.0)
        : 0.0;

    final trafficUsedGb = sub.trafficUsedBytes / (1024 * 1024 * 1024);
    final trafficLimitGb = sub.trafficLimitBytes / (1024 * 1024 * 1024);
    final trafficRatio = subState?.trafficUsageRatio ?? 0.0;

    // Resolve plan name from planId
    final planName = _getPlanName(sub, subState);
    final isTrial = sub.status == SubscriptionStatus.trial;

    final cards = <Widget>[
      // Card 1: Current Plan
      _StatsCard(
        key: const Key('stats_plan'),
        icon: Icons.workspace_premium_outlined,
        label: l10n.currentPlan,
        value: planName ?? l10n.profileStatsNoPlan,
        accentColor: sub != null
            ? _statusColor(sub.status)
            : null,
        badge: _buildPlanBadge(sub, isTrial, daysRemaining, l10n),
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

      // Card 3: Days Remaining with Expiry Date
      _StatsCard(
        key: const Key('stats_days'),
        icon: Icons.calendar_today_outlined,
        label: l10n.profileStatsDaysLeft,
        value: '$daysRemaining',
        subtitle: 'Expires ${DateFormat.yMMMd().format(sub.endDate)}',
        progress: daysProgress,
        accentColor: daysRemaining < 7
            ? const Color(0xFFFF5252)
            : daysRemaining < 30
                ? const Color(0xFFFFAB40)
                : CyberColors.matrixGreen,
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
        final isLandscape = ResponsiveLayout.isLandscape(context);
        final columns = ResponsiveLayout.adaptiveGridColumnsForOrientation(
          constraints.maxWidth,
          landscape: isLandscape,
        );
        final totalGapWidth = Spacing.sm * (columns - 1);
        final cardWidth = (constraints.maxWidth - totalGapWidth) / columns;
        return Wrap(
          spacing: Spacing.sm,
          runSpacing: Spacing.sm,
          children: [
            for (int i = 0; i < cards.length; i++)
              SizedBox(
                width: cardWidth,
                child: StaggeredListItem(
                  index: i,
                  child: cards[i],
                ),
              ),
          ],
        );
      },
    );
  }

  /// Resolves the plan name from the subscription's planId.
  String? _getPlanName(SubscriptionEntity? sub, SubscriptionState? state) {
    if (sub == null || state == null) return null;

    try {
      final plan = state.availablePlans.firstWhere(
        (p) => p.id == sub.planId,
      );
      return plan.name;
    } catch (_) {
      // Plan not found in available plans list - return planId as fallback
      return sub.planId;
    }
  }

  /// Builds the appropriate badge text based on subscription state.
  String? _buildPlanBadge(
    SubscriptionEntity? sub,
    bool isTrial,
    int daysRemaining,
    AppLocalizations l10n,
  ) {
    if (sub == null) return null;

    // Trial badge with days remaining
    if (isTrial) {
      return '${l10n.profileSubTrial} • $daysRemaining ${l10n.profileStatsDaysLeft}';
    }

    // Auto-renew indicator for active subscriptions
    if (sub.cancelledAt == null && sub.status == SubscriptionStatus.active) {
      return l10n.profileAutoRenew;
    }

    return null;
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
    this.subtitle,
    this.progress,
    this.accentColor,
    this.badge,
  });

  final IconData icon;
  final String label;
  final String value;
  final String? subtitle;
  final double? progress;
  final Color? accentColor;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final accent = accentColor ?? colorScheme.primary;

    // Build combined semantic label: "Traffic: 2.5 / 10 GB"
    final semanticLabel = '$label: $value';
    final progressHint = progress != null
        ? ', ${(progress! * 100).toInt()} percent used'
        : '';

    return Semantics(
      label: '$semanticLabel$progressHint',
      hint: 'Displays your $label stat',
      readOnly: true,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Icon row
              ExcludeSemantics(
                child: Container(
                  padding: const EdgeInsets.all(Spacing.sm),
                  decoration: BoxDecoration(
                    color: accent.withAlpha(25),
                    borderRadius: BorderRadius.circular(Radii.sm),
                  ),
                  child: Icon(icon, size: 20, color: accent),
                ),
              ),
              const SizedBox(height: Spacing.sm),

              // Label
              ExcludeSemantics(
                child: Text(
                  label,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(height: Spacing.xs),

              // Value
              ExcludeSemantics(
                child: Text(
                  value,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),

              // Optional subtitle
              if (subtitle != null) ...[
                const SizedBox(height: Spacing.xs),
                ExcludeSemantics(
                  child: Text(
                    subtitle!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],

              // Optional badge
              if (badge != null) ...[
                const SizedBox(height: Spacing.xs),
                ExcludeSemantics(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: Spacing.xs,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: CyberColors.matrixGreen.withAlpha(40),
                      borderRadius: BorderRadius.circular(Radii.xs),
                    ),
                    child: Text(
                      badge!,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: CyberColors.matrixGreen,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ],

              // Optional progress bar
              if (progress != null) ...[
                const SizedBox(height: Spacing.sm),
                ExcludeSemantics(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(Radii.sm),
                    child: LinearProgressIndicator(
                      value: progress,
                      minHeight: 4,
                      backgroundColor: colorScheme.surfaceContainerHighest,
                      valueColor: AlwaysStoppedAnimation<Color>(accent),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// No Subscription Card
// ---------------------------------------------------------------------------

class _NoSubscriptionCard extends ConsumerWidget {
  const _NoSubscriptionCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);
    final haptics = ref.read(hapticServiceProvider);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icon
            Container(
              padding: const EdgeInsets.all(Spacing.md),
              decoration: BoxDecoration(
                color: CyberColors.matrixGreen.withAlpha(25),
                borderRadius: BorderRadius.circular(Radii.md),
              ),
              child: const Icon(
                Icons.rocket_launch_outlined,
                size: 32,
                color: CyberColors.matrixGreen,
              ),
            ),
            const SizedBox(height: Spacing.md),

            // Title
            Text(
              l10n.profileStatsNoPlan,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: Spacing.xs),

            // Description
            Text(
              'Get secure, fast VPN access with premium features',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.md),

            // CTA Button
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () {
                  unawaited(haptics.selection());
                  unawaited(context.push('/subscribe'));
                },
                icon: const Icon(Icons.arrow_forward),
                label: Text(l10n.upgradePlan),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Quick Actions Section
// ---------------------------------------------------------------------------

class _QuickActionsSection extends ConsumerWidget {
  const _QuickActionsSection({
    required this.hasSubscription,
    this.subscription,
  });

  final bool hasSubscription;
  final SubscriptionEntity? subscription;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final haptics = ref.read(hapticServiceProvider);

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
            unawaited(haptics.selection());
            unawaited(context.push('/subscribe'));
          },
        ),

        // Invite Friends
        _QuickActionButton(
          key: const Key('action_invite'),
          icon: Icons.people_outline,
          label: l10n.profileInviteFriends,
          onTap: () {
            unawaited(haptics.selection());
            unawaited(context.push('/referral'));
          },
        ),

        // Security Settings
        _QuickActionButton(
          key: const Key('action_security'),
          icon: Icons.security_outlined,
          label: l10n.profileSecuritySettings,
          onTap: () {
            unawaited(haptics.selection());
            unawaited(context.push('/profile/2fa'));
          },
        ),

        // Cancel Subscription (only shown if user has active subscription)
        if (hasSubscription && subscription != null)
          _QuickActionButton(
            key: const Key('action_cancel_subscription'),
            icon: Icons.cancel_outlined,
            label: l10n.subscriptionCancelButton,
            onTap: () async {
              unawaited(haptics.selection());
              final result = await CancelSubscriptionSheet.show(
                context,
                subscription!.id,
              );
              if (result == true && context.mounted) {
                // Refresh subscription data after cancellation
                unawaited(
                  ref.read(subscriptionProvider.notifier).loadSubscription(),
                );
              }
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
      child: Semantics(
        label: label,
        hint: 'Double tap to open $label',
        button: true,
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
                  ExcludeSemantics(
                    child: Icon(icon, color: colorScheme.primary),
                  ),
                  const SizedBox(width: Spacing.md),
                  Expanded(
                    child: ExcludeSemantics(
                      child: Text(
                        label,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                  ExcludeSemantics(
                    child: Icon(
                      Directionality.of(context) == TextDirection.rtl
                          ? Icons.chevron_left
                          : Icons.chevron_right,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
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
