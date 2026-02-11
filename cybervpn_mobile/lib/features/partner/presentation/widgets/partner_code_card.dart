import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';
import 'package:cybervpn_mobile/features/partner/presentation/providers/partner_provider.dart';

// ---------------------------------------------------------------------------
// PartnerCodeCard
// ---------------------------------------------------------------------------

/// Displays a single partner code with its details and actions.
///
/// Shows the code, markup, client count, active status, and provides
/// copy, share, toggle active, and edit markup actions.
class PartnerCodeCard extends ConsumerWidget {
  const PartnerCodeCard({
    super.key,
    required this.code,
  });

  final PartnerCode code;

  // ---- Actions ------------------------------------------------------------

  Future<void> _onCopy(BuildContext context, WidgetRef ref) async {
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    await Clipboard.setData(ClipboardData(text: code.code));
    if (context.mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.partnerCodeCopied),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _onShare(BuildContext context, WidgetRef ref) async {
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    await ref.read(partnerProvider.notifier).shareCode(code.code);
  }

  Future<void> _onToggleActive(BuildContext context, WidgetRef ref) async {
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    final result = await ref.read(partnerProvider.notifier).toggleCodeStatus(
          code: code.code,
          isActive: !code.isActive,
        );

    if (context.mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result is Success
                ? l10n.partnerCodeStatusUpdated
                : l10n.errorOccurred,
          ),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _onEditMarkup(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final controller = TextEditingController(text: code.markup.toString());

    final newMarkup = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.partnerEditMarkup),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(
            labelText: l10n.partnerMarkupPercentage,
            suffixText: '%',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () {
              final value = double.tryParse(controller.text);
              if (value != null && value >= 0 && value <= 100) {
                Navigator.of(context).pop(value);
              }
            },
            child: Text(l10n.commonSave),
          ),
        ],
      ),
    );

    if (newMarkup != null && context.mounted) {
      final result = await ref.read(partnerProvider.notifier).updateMarkup(
            code: code.code,
            markup: newMarkup,
          );

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result is Success
                  ? l10n.partnerMarkupUpdated
                  : l10n.errorOccurred,
            ),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  // ---- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final colorScheme = theme.colorScheme;

    final statusColor =
        code.isActive ? CyberColors.matrixGreen : colorScheme.error;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Code and status row
            Row(
              children: [
                Expanded(
                  child: Text(
                    code.code,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontFamily: 'JetBrains Mono',
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.5,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: Spacing.sm,
                    vertical: Spacing.xs,
                  ),
                  decoration: BoxDecoration(
                    color: statusColor.withAlpha(25),
                    borderRadius: BorderRadius.circular(Radii.sm),
                  ),
                  child: Text(
                    code.isActive ? l10n.partnerCodeActive : l10n.partnerCodeInactive,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: statusColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: Spacing.sm),

            // Description (if available)
            if (code.description != null) ...[
              Text(
                code.description!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: Spacing.sm),
            ],

            // Stats row
            Row(
              children: [
                Icon(
                  Icons.percent_outlined,
                  size: 16,
                  color: colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: Spacing.xs),
                Text(
                  l10n.partnerMarkupLabel('${code.markup.toStringAsFixed(1)}%'),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(width: Spacing.md),
                Icon(
                  Icons.group_outlined,
                  size: 16,
                  color: colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: Spacing.xs),
                Text(
                  l10n.partnerClientCountLabel(code.clientCount),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                const Spacer(),
                Text(
                  l10n.partnerCreatedDate(DateFormat.yMMMd().format(code.createdAt)),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            const SizedBox(height: Spacing.md),

            // Action buttons
            Wrap(
              spacing: Spacing.sm,
              runSpacing: Spacing.sm,
              children: [
                OutlinedButton.icon(
                  onPressed: () => _onCopy(context, ref),
                  icon: const Icon(Icons.copy_outlined, size: 18),
                  label: Text(l10n.partnerCopyCode),
                ),
                OutlinedButton.icon(
                  onPressed: () => _onShare(context, ref),
                  icon: const Icon(Icons.share_outlined, size: 18),
                  label: Text(l10n.commonShare),
                ),
                OutlinedButton.icon(
                  onPressed: () => _onEditMarkup(context, ref),
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  label: Text(l10n.partnerEditMarkup),
                ),
                OutlinedButton.icon(
                  onPressed: () => _onToggleActive(context, ref),
                  icon: Icon(
                    code.isActive ? Icons.pause_outlined : Icons.play_arrow_outlined,
                    size: 18,
                  ),
                  label: Text(
                    code.isActive ? l10n.partnerDeactivate : l10n.partnerActivate,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
