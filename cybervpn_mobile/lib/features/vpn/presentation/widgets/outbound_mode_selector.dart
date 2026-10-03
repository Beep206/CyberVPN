import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

/// A segmented selector allowing users to switch between outbound traffic modes:
/// - [OutboundMode.rule]: Smart routing based on rules (RU bypass, AdBlock, etc.)
/// - [OutboundMode.global]: 100% of traffic routes through the VPN tunnel
/// - [OutboundMode.direct]: All traffic bypasses the VPN tunnel
class OutboundModeSelector extends ConsumerWidget {
  const OutboundModeSelector({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider).value ?? const AppSettings();
    final currentMode = settings.outboundMode;
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Semantics(
      label: l10n.outboundModeTooltip,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: SegmentedButton<OutboundMode>(
              showSelectedIcon: false,
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                padding: WidgetStateProperty.all(
                  const EdgeInsets.symmetric(
                    horizontal: Spacing.sm,
                    vertical: 2,
                  ),
                ),
                textStyle: WidgetStateProperty.all(
                  theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
              ),
              segments: [
                ButtonSegment<OutboundMode>(
                  value: OutboundMode.rule,
                  icon: const Icon(Icons.alt_route, size: 16),
                  label: Text(l10n.outboundModeRule),
                  tooltip: l10n.outboundModeRule,
                ),
                ButtonSegment<OutboundMode>(
                  value: OutboundMode.global,
                  icon: const Icon(Icons.public, size: 16),
                  label: Text(l10n.outboundModeGlobal),
                  tooltip: l10n.outboundModeGlobal,
                ),
                ButtonSegment<OutboundMode>(
                  value: OutboundMode.direct,
                  icon: const Icon(Icons.near_me_outlined, size: 16),
                  label: Text(l10n.outboundModeDirect),
                  tooltip: l10n.outboundModeDirect,
                ),
              ],
              selected: {currentMode},
              onSelectionChanged: (newSelection) {
                if (newSelection.isEmpty) return;
                final selected = newSelection.first;
                if (selected == currentMode) return;

                unawaited(ref.read(hapticServiceProvider).selection());
                unawaited(
                  ref
                      .read(settingsProvider.notifier)
                      .updateOutboundMode(selected),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
