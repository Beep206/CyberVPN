import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/referral/presentation/widgets/referral_qr_widget.dart';

// ---------------------------------------------------------------------------
// ReferralCodeCard
// ---------------------------------------------------------------------------

/// Displays the user's referral code with copy, share, and QR code actions.
///
/// The card shows the referral code in a monospace font with:
/// - A copy button that copies to clipboard with haptic feedback.
/// - A share button that opens the system share sheet.
/// - A QR code of the referral link below the code.
class ReferralCodeCard extends ConsumerWidget {
  const ReferralCodeCard({
    super.key,
    required this.referralCode,
    required this.referralLink,
  });

  /// The user's unique referral code.
  final String referralCode;

  /// The full referral link to share and encode in QR.
  final String referralLink;

  // ---- Actions ------------------------------------------------------------

  Future<void> _onCopy(BuildContext context, WidgetRef ref) async {
    // Trigger impact haptic on successful copy to clipboard.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    await Clipboard.setData(ClipboardData(text: referralCode));
    if (context.mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.referralCodeCopied),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _onShare(BuildContext context, WidgetRef ref) async {
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    final l10n = AppLocalizations.of(context);
    await share_plus.SharePlus.instance.share(share_plus.ShareParams(
      text: l10n.referralShareMessage(referralLink),
    ));
  }

  // ---- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section title
            Text(
              l10n.referralCodeLabel,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: Spacing.md),

            // Code display with actions
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: Spacing.md,
                vertical: Spacing.sm,
              ),
              decoration: BoxDecoration(
                color: colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(Radii.sm),
                border: Border.all(
                  color: colorScheme.primary.withAlpha(60),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: SelectableText(
                      referralCode,
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontFamily: 'JetBrains Mono',
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2.0,
                        color: colorScheme.primary,
                      ),
                    ),
                  ),
                  IconButton(
                    key: const Key('btn_copy_code'),
                    icon: const Icon(Icons.copy_outlined),
                    tooltip: l10n.referralCopyCode,
                    onPressed: () => _onCopy(context, ref),
                  ),
                  IconButton(
                    key: const Key('btn_share_code'),
                    icon: const Icon(Icons.share_outlined),
                    tooltip: l10n.commonShare,
                    onPressed: () => _onShare(context, ref),
                  ),
                ],
              ),
            ),
            const SizedBox(height: Spacing.md),

            // QR code
            Center(
              child: ReferralQrWidget(data: referralLink),
            ),
          ],
        ),
      ),
    );
  }
}
