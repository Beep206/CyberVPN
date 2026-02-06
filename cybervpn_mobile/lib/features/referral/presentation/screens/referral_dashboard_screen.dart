import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:cybervpn_mobile/features/referral/presentation/providers/referral_provider.dart';
import 'package:cybervpn_mobile/features/referral/presentation/widgets/referral_code_card.dart';
import 'package:cybervpn_mobile/features/referral/presentation/widgets/referral_stats_card.dart';

// ---------------------------------------------------------------------------
// ReferralDashboardScreen
// ---------------------------------------------------------------------------

/// Referral dashboard with code sharing, stats, QR code, and a "coming soon"
/// fallback when the backend does not yet support the referral feature.
///
/// Watches [referralProvider] for reactive state updates. Displays:
/// - **Available**: Referral code card (copy, share, QR), stats grid,
///   recent referrals list.
/// - **Unavailable**: "Coming Soon" placeholder with a "Notify Me" button.
///
/// Supports pull-to-refresh and manual refresh via the AppBar action.
class ReferralDashboardScreen extends ConsumerWidget {
  const ReferralDashboardScreen({super.key});

  /// Base URL for constructing referral links.
  static const _referralBaseUrl = 'https://cybervpn.app/ref/';

  // ---- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncReferral = ref.watch(referralProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Referrals'),
        actions: [
          IconButton(
            key: const Key('btn_refresh_referral'),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () {
              unawaited(ref.read(referralProvider.notifier).checkAvailability());
            },
          ),
        ],
      ),
      body: asyncReferral.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorBody(
          message: error.toString(),
          onRetry: () => ref.invalidate(referralProvider),
        ),
        data: (state) {
          if (!state.isAvailable) {
            return const _ComingSoonBody();
          }
          return _AvailableBody(state: state);
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Available Body
// ---------------------------------------------------------------------------

/// Full referral dashboard rendered when the feature is available.
class _AvailableBody extends StatelessWidget {
  const _AvailableBody({required this.state});

  final ReferralState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final code = state.referralCode ?? '';
    final referralLink = '${ReferralDashboardScreen._referralBaseUrl}$code';

    return ListView(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.md,
      ),
      children: [
        // -- Referral code card --
        if (code.isNotEmpty)
          ReferralCodeCard(
            key: const Key('referral_code_card'),
            referralCode: code,
            referralLink: referralLink,
          ),

        if (code.isNotEmpty) const SizedBox(height: Spacing.lg),

        // -- Stats grid --
        if (state.stats != null) ...[
          Text(
            'Your Stats',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: Spacing.sm),
          ReferralStatsCard(
            key: const Key('referral_stats'),
            stats: state.stats!,
          ),
          const SizedBox(height: Spacing.lg),
        ],

        // -- Recent referrals --
        Text(
          'Recent Referrals',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),

        if (state.recentReferrals.isEmpty)
          _EmptyReferralsPlaceholder()
        else
          ...state.recentReferrals.map(
            (entry) => _ReferralEntryTile(
              key: ValueKey('referral_${entry.code}_${entry.joinDate}'),
              entry: entry,
            ),
          ),

        // Bottom padding for navigation bar clearance.
        const SizedBox(height: 80),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Referral Entry Tile
// ---------------------------------------------------------------------------

class _ReferralEntryTile extends StatelessWidget {
  const _ReferralEntryTile({super.key, required this.entry});

  final ReferralEntry entry;

  Color _statusColor(ReferralStatus status) {
    return switch (status) {
      ReferralStatus.completed => CyberColors.matrixGreen,
      ReferralStatus.active => CyberColors.neonCyan,
      ReferralStatus.pending => const Color(0xFFFFAB40),
    };
  }

  String _statusLabel(ReferralStatus status) {
    return switch (status) {
      ReferralStatus.completed => 'Completed',
      ReferralStatus.active => 'Active',
      ReferralStatus.pending => 'Pending',
    };
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final statusColor = _statusColor(entry.status);

    return Card(
      margin: const EdgeInsets.only(bottom: Spacing.sm),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: statusColor.withAlpha(25),
          child: Icon(
            Icons.person_outline,
            color: statusColor,
            size: 20,
          ),
        ),
        title: Text(
          entry.code,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Text(
          'Joined ${DateFormat.yMMMd().format(entry.joinDate)}',
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.sm,
            vertical: Spacing.xs,
          ),
          decoration: BoxDecoration(
            color: statusColor.withAlpha(25),
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: Text(
            _statusLabel(entry.status),
            style: theme.textTheme.labelSmall?.copyWith(
              color: statusColor,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty Referrals Placeholder
// ---------------------------------------------------------------------------

class _EmptyReferralsPlaceholder extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      key: const Key('empty_referrals'),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: Spacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.people_outline,
              size: 48,
              color: colorScheme.onSurfaceVariant.withAlpha(100),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              'No referrals yet',
              style: theme.textTheme.bodyLarge?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.xs),
            Text(
              'Share your code to start earning rewards!',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant.withAlpha(180),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Coming Soon Body
// ---------------------------------------------------------------------------

/// Placeholder UI when the referral system is not yet available.
///
/// Shows an icon illustration, headline, subtitle, and a "Notify Me" button
/// that displays a confirmation SnackBar.
class _ComingSoonBody extends StatelessWidget {
  const _ComingSoonBody();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      key: const Key('coming_soon_body'),
      child: Padding(
        padding: const EdgeInsets.all(Spacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Illustration icon
            Container(
              padding: const EdgeInsets.all(Spacing.xl),
              decoration: BoxDecoration(
                color: colorScheme.primary.withAlpha(20),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.card_giftcard_outlined,
                size: 64,
                color: colorScheme.primary,
              ),
            ),
            const SizedBox(height: Spacing.lg),

            // Headline
            Text(
              'Referral Program Coming Soon',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.sm),

            // Subtitle
            Text(
              'Invite friends and earn rewards when they subscribe. '
              'Stay tuned for our upcoming referral program!',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.xl),

            // Notify Me button
            FilledButton.icon(
              key: const Key('btn_notify_me'),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text("We'll notify you when referrals launch!"),
                    duration: Duration(seconds: 3),
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              },
              icon: const Icon(Icons.notifications_active_outlined),
              label: const Text('Notify Me'),
            ),
          ],
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
                child: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
