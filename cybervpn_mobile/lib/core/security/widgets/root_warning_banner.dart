import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/security/device_integrity.dart';

/// Persistent warning banner shown when a rooted/jailbroken device is detected.
///
/// In [RootEnforcementPolicy.logging] mode, displays an informational warning.
/// In [RootEnforcementPolicy.blocking] mode, displays a stronger warning
/// indicating VPN is unavailable.
///
/// The banner can be dismissed, and the dismissal is persisted to
/// [SharedPreferences] so it won't reappear.
class RootWarningBanner extends ConsumerWidget {
  const RootWarningBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isRooted = ref.watch(isDeviceRootedProvider).value ?? false;
    final isDismissed = ref.watch(rootWarningDismissedProvider).value ?? false;
    final checker = ref.watch(deviceIntegrityCheckerProvider);

    // Only show when device is rooted AND user hasn't dismissed.
    final shouldShow = isRooted && !isDismissed;

    if (!shouldShow) return const SizedBox.shrink();

    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final isBlocking = checker.isBlockingEnabled;

    return MaterialBanner(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      leading: Icon(
        isBlocking ? Icons.block : Icons.warning_amber_rounded,
        color: isBlocking
            ? theme.colorScheme.error
            : theme.colorScheme.tertiary,
      ),
      backgroundColor: isBlocking
          ? theme.colorScheme.errorContainer
          : theme.colorScheme.tertiaryContainer,
      content: Text(
        isBlocking
            ? l10n.rootDetectionBannerBlocking
            : l10n.rootDetectionBannerWarning,
        style: theme.textTheme.bodySmall?.copyWith(
          color: isBlocking
              ? theme.colorScheme.onErrorContainer
              : theme.colorScheme.onTertiaryContainer,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () async {
            await checker.dismissWarning();
            ref.invalidate(rootWarningDismissedProvider);
          },
          child: Text(l10n.rootDetectionDialogDismiss),
        ),
      ],
    );
  }
}
