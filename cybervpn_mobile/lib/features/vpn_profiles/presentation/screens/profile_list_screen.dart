import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lottie/lottie.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/widgets/profile_card.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_refresh_indicator.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';
import 'package:cybervpn_mobile/shared/widgets/skeleton_loader.dart';
import 'package:cybervpn_mobile/shared/widgets/staggered_list_item.dart';

/// Main screen listing all VPN profiles.
///
/// Features:
/// - Pull-to-refresh
/// - Empty state with Lottie animation
/// - Loading shimmer skeleton
/// - Error state with retry
/// - FAB to add new profile
/// - Staggered fade-in animations for list items
///
/// Currently renders with mock data until notifiers (UI-5) are wired.
class ProfileListScreen extends ConsumerWidget {
  const ProfileListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);

    // TODO(ui-5): Replace mock data with actual provider once ProfileListNotifier is wired.
    final profiles = _mockProfiles();

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: l10n.profiles,
          style: Theme.of(context).appBarTheme.titleTextStyle,
        ),
      ),
      body: profiles.isEmpty
          ? _EmptyState(l10n: l10n)
          : _ProfileList(profiles: profiles),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          // TODO(ui-3): Navigate to AddProfileScreen
        },
        icon: const Icon(Icons.add),
        label: Text(l10n.addProfile),
      ),
    );
  }
}

/// The scrollable list of profile cards with pull-to-refresh.
class _ProfileList extends StatelessWidget {
  const _ProfileList({required this.profiles});

  final List<VpnProfile> profiles;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return CyberRefreshIndicator(
      onRefresh: () async {
        // TODO(ui-5): Trigger refresh via notifier
        await Future<void>.delayed(const Duration(seconds: 1));
      },
      child: CustomScrollView(
        slivers: [
          // Subtitle
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                Spacing.md,
                Spacing.sm,
                Spacing.md,
                Spacing.xs,
              ),
              child: Text(
                l10n.profilesSubtitle,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ),

          // Profile cards
          SliverList.builder(
            itemCount: profiles.length,
            itemBuilder: (context, index) {
              final profile = profiles[index];
              return StaggeredListItem(
                index: index,
                child: ProfileCard(
                  profile: profile,
                  onTap: () {
                    // TODO(ui-2): Navigate to ProfileDetailScreen
                  },
                ),
              );
            },
          ),

          // Bottom clearance
          SliverPadding(
            padding: EdgeInsets.only(
              bottom: Spacing.navBarClearance(context),
            ),
          ),
        ],
      ),
    );
  }
}

/// Empty state shown when no profiles exist.
class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Lottie.asset(
              'assets/animations/empty_state.json',
              width: 160,
              height: 160,
              fit: BoxFit.contain,
              animate: !MediaQuery.of(context).disableAnimations,
            ),
            const SizedBox(height: Spacing.lg),
            Text(
              l10n.profileEmpty,
              style: theme.textTheme.titleMedium?.copyWith(
                fontFamily: 'Orbitron',
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              l10n.profileEmptySubtitle,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Loading skeleton for the profile list.
///
/// Used as a placeholder while profiles are being fetched.
class ProfileListSkeleton extends StatelessWidget {
  const ProfileListSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: Spacing.sm),
      itemCount: 3,
      itemBuilder: (context, index) {
        return const Padding(
          padding: EdgeInsets.symmetric(
            horizontal: Spacing.md,
            vertical: Spacing.xs,
          ),
          child: SkeletonCard(
            height: 130,
            borderRadius: Radii.md,
          ),
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Mock data — will be removed once providers are wired (UI-5)
// ---------------------------------------------------------------------------

List<VpnProfile> _mockProfiles() {
  final now = DateTime.now();
  return [
    VpnProfile.remote(
      id: 'mock-1',
      name: 'CyberVPN Premium',
      subscriptionUrl: 'https://example.com/sub/abc123',
      isActive: true,
      sortOrder: 0,
      createdAt: now.subtract(const Duration(days: 30)),
      lastUpdatedAt: now.subtract(const Duration(hours: 2)),
      uploadBytes: 1024 * 1024 * 512, // 512 MB
      downloadBytes: 1024 * 1024 * 1024 * 3, // 3 GB
      totalBytes: 1024 * 1024 * 1024 * 50, // 50 GB
      expiresAt: now.add(const Duration(days: 25)),
      servers: [],
    ),
    VpnProfile.remote(
      id: 'mock-2',
      name: 'Work VPN',
      subscriptionUrl: 'https://vpn.company.com/sub',
      isActive: false,
      sortOrder: 1,
      createdAt: now.subtract(const Duration(days: 90)),
      lastUpdatedAt: now.subtract(const Duration(days: 3)),
      uploadBytes: 1024 * 1024 * 200,
      downloadBytes: 1024 * 1024 * 800,
      totalBytes: 0, // unlimited
      expiresAt: now.subtract(const Duration(days: 5)),
      servers: [],
    ),
    VpnProfile.local(
      id: 'mock-3',
      name: 'Custom Config',
      isActive: false,
      sortOrder: 2,
      createdAt: now.subtract(const Duration(days: 7)),
      lastUpdatedAt: now.subtract(const Duration(days: 1)),
      servers: [],
    ),
  ];
}
