import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_card.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

/// Choice screen for adding a new VPN profile.
///
/// Presents import methods:
/// - Subscription URL (navigates to [AddByUrlScreen])
/// - QR Code scan
/// - Clipboard import
///
/// Each option is displayed as a [CyberCard] with an icon, title, and
/// description.
class AddProfileScreen extends ConsumerWidget {
  const AddProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: l10n.addProfile,
          style: theme.appBarTheme.titleTextStyle,
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.md,
          vertical: Spacing.md,
        ),
        children: [
          _ImportOptionCard(
            icon: Icons.link,
            title: l10n.addProfileByUrl,
            description: l10n.addProfileByUrlDesc,
            color: CyberColors.neonCyan,
            onTap: () {
              // TODO(routing): Navigate to AddByUrlScreen
            },
          ),
          const SizedBox(height: Spacing.sm),
          _ImportOptionCard(
            icon: Icons.qr_code_scanner,
            title: l10n.addProfileByQr,
            description: l10n.addProfileByQrDesc,
            color: CyberColors.neonPink,
            onTap: () {
              // TODO(routing): Navigate to QR scanner
            },
          ),
          const SizedBox(height: Spacing.sm),
          _ImportOptionCard(
            icon: Icons.content_paste,
            title: l10n.addProfileByClipboard,
            description: l10n.addProfileByClipboardDesc,
            color: CyberColors.matrixGreen,
            onTap: () {
              // TODO(ui-5): Import from clipboard via notifier
            },
          ),
        ],
      ),
    );
  }
}

/// A single import method option card.
class _ImportOptionCard extends StatelessWidget {
  const _ImportOptionCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GestureDetector(
      onTap: onTap,
      child: CyberCard(
        color: color,
        isAnimated: false,
        child: Row(
          children: [
            // Icon container
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(Radii.md),
                border: Border.all(color: color.withValues(alpha: 0.3)),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(width: Spacing.md),

            // Title + description
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontFamily: 'Orbitron',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: Spacing.xs),
                  Text(
                    description,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),

            // Chevron
            Icon(
              Icons.chevron_right,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }
}
