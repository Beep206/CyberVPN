import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_badge.dart';

/// Compact horizontal widget showing the active VPN profile with a
/// dropdown indicator. Tapping opens a bottom sheet for quick profile
/// switching.
///
/// Designed to sit in the connection screen top bar area. Adapts to
/// the cyberpunk theme with neon accents.
class ProfileSelectorWidget extends ConsumerWidget {
  const ProfileSelectorWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeProfileAsync = ref.watch(activeVpnProfileProvider);
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return activeProfileAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, _) => const SizedBox.shrink(),
      data: (activeProfile) {
        if (activeProfile == null) return const SizedBox.shrink();

        return Semantics(
          label: l10n.profiles,
          hint: 'Tap to switch VPN profile',
          button: true,
          child: InkWell(
            onTap: () => _showProfileSwitcher(context, ref),
            borderRadius: BorderRadius.circular(Radii.md),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: Spacing.sm + 2,
                vertical: Spacing.xs + 1,
              ),
              decoration: BoxDecoration(
                color: CyberColors.neonCyan.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(Radii.md),
                border: Border.all(
                  color: CyberColors.neonCyan.withValues(alpha: 0.25),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    activeProfile is RemoteVpnProfile
                        ? Icons.cloud_outlined
                        : Icons.folder_outlined,
                    size: 14,
                    color: CyberColors.neonCyan,
                  ),
                  const SizedBox(width: Spacing.xs),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 120),
                    child: Text(
                      activeProfile.name,
                      style: theme.textTheme.labelSmall?.copyWith(
                        fontFamily: 'JetBrains Mono',
                        fontWeight: FontWeight.w600,
                        color: CyberColors.neonCyan,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: Spacing.xs),
                  Icon(
                    Icons.expand_more,
                    size: 14,
                    color: CyberColors.neonCyan.withValues(alpha: 0.7),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  void _showProfileSwitcher(BuildContext context, WidgetRef ref) {
    unawaited(showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _ProfileSwitcherSheet(ref: ref),
    ));
  }
}

/// Bottom sheet listing all profiles for quick switching.
class _ProfileSwitcherSheet extends StatelessWidget {
  const _ProfileSwitcherSheet({required this.ref});

  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final profilesAsync = ref.watch(profileListProvider);
    final activeProfileAsync = ref.watch(activeVpnProfileProvider);

    return DraggableScrollableSheet(
      initialChildSize: 0.4,
      minChildSize: 0.25,
      maxChildSize: 0.7,
      expand: false,
      builder: (context, scrollController) {
        return Column(
          children: [
            // Handle bar
            Padding(
              padding: const EdgeInsets.symmetric(vertical: Spacing.sm),
              child: Container(
                width: 32,
                height: 4,
                decoration: BoxDecoration(
                  color: theme.colorScheme.onSurfaceVariant.withValues(
                    alpha: 0.4,
                  ),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Title
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: Spacing.md,
                vertical: Spacing.xs,
              ),
              child: Row(
                children: [
                  Text(
                    l10n.profiles,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontFamily: 'Orbitron',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  TextButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      // TODO(routing): Navigate to AddProfileScreen
                    },
                    icon: const Icon(Icons.add, size: 18),
                    label: Text(l10n.addProfile),
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Profile list
            Expanded(
              child: profilesAsync.when(
                loading: () => const Center(
                  child: CircularProgressIndicator(value: null),
                ),
                error: (error, _) => Center(
                  child: Text(
                    l10n.errorOccurred,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
                data: (profiles) {
                  if (profiles.isEmpty) {
                    return Center(
                      child: Text(
                        l10n.profileEmpty,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    );
                  }

                  final activeId = activeProfileAsync.value?.id;

                  return ListView.builder(
                    controller: scrollController,
                    itemCount: profiles.length,
                    itemBuilder: (context, index) {
                      final profile = profiles[index];
                      final isActive = profile.id == activeId;

                      return _ProfileSwitchTile(
                        profile: profile,
                        isActive: isActive,
                        onTap: () => _onProfileTap(context, profile, isActive),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _onProfileTap(
    BuildContext context,
    VpnProfile profile,
    bool isActive,
  ) async {
    if (isActive) {
      Navigator.of(context).pop();
      return;
    }

    // TODO(ui-5): Check if VPN is connected and show disconnect confirmation
    final result = await ref
        .read(switchActiveProfileUseCaseProvider)
        .call(profile.id);

    if (!context.mounted) return;

    switch (result) {
      case Success():
        Navigator.of(context).pop();
      case Failure(:final failure):
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(failure.toString()),
            behavior: SnackBarBehavior.floating,
          ),
        );
    }
  }
}

/// A single tile in the profile switcher bottom sheet.
class _ProfileSwitchTile extends StatelessWidget {
  const _ProfileSwitchTile({
    required this.profile,
    required this.isActive,
    required this.onTap,
  });

  final VpnProfile profile;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return ListTile(
      onTap: onTap,
      leading: Icon(
        profile is RemoteVpnProfile
            ? Icons.cloud_outlined
            : Icons.folder_outlined,
        color: isActive
            ? CyberColors.matrixGreen
            : theme.colorScheme.onSurfaceVariant,
      ),
      title: Text(
        profile.name,
        style: theme.textTheme.bodyMedium?.copyWith(
          fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
          color: isActive ? CyberColors.matrixGreen : null,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        l10n.profileServers(profile.servers.length),
        style: theme.textTheme.bodySmall?.copyWith(
          fontFamily: 'JetBrains Mono',
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
      trailing: isActive
          ? CyberBadge(
              label: l10n.profileActive,
              color: CyberColors.matrixGreen,
              icon: Icons.check_circle,
            )
          : const Icon(Icons.chevron_right, size: 20),
    );
  }
}
