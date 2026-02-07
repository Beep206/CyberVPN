import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

// ---------------------------------------------------------------------------
// AppearanceScreen
// ---------------------------------------------------------------------------

/// Settings sub-screen for appearance preferences.
///
/// Provides controls for:
/// - Theme mode (Material You / Cyberpunk) with preview thumbnails
/// - Brightness (System / Light / Dark) via segmented button
/// - Dynamic color toggle (Android 12+ with Material You only)
class AppearanceScreen extends ConsumerWidget {
  const AppearanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSettings = ref.watch(settingsProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.settingsAppearance),
      ),
      body: asyncSettings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildError(context, ref, error),
        data: (settings) => _buildBody(context, ref, settings),
      ),
    );
  }

  // -- Error state -----------------------------------------------------------

  Widget _buildError(BuildContext context, WidgetRef ref, Object error) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text(
            l10n.settingsAppearanceLoadError,
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: Text(l10n.retry),
          ),
        ],
      ),
    );
  }

  // -- Data state ------------------------------------------------------------

  Widget _buildBody(
    BuildContext context,
    WidgetRef ref,
    AppSettings settings,
  ) {
    final notifier = ref.read(settingsProvider.notifier);
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    final l10n = AppLocalizations.of(context);

    return ListView(
      children: [
        // --- Theme Mode ---
        SettingsSection(
          title: l10n.settingsThemeModeLabel,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              child: _ThemeModePicker(
                selected: settings.themeMode,
                onChanged: notifier.updateThemeMode,
              ),
            ),
          ],
        ),

        // --- Brightness ---
        SettingsSection(
          title: l10n.settingsBrightnessSection,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              child: _BrightnessSegmentedButton(
                selected: settings.brightness,
                onChanged: notifier.updateBrightness,
              ),
            ),
          ],
        ),

        // --- Text Size ---
        SettingsSection(
          title: l10n.settingsTextSizeSection,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              child: _TextScalePicker(
                selected: settings.textScale,
                onChanged: notifier.updateTextScale,
              ),
            ),
          ],
        ),

        // --- Dynamic Color (only on Android 12+ with Material You) ---
        if (_shouldShowDynamicColor(settings.themeMode))
          SettingsSection(
            title: l10n.settingsDynamicColorLabel,
            children: [
              SettingsTile.toggle(
                key: const Key('tile_dynamic_color'),
                title: l10n.settingsDynamicColorLabel,
                subtitle: l10n.settingsDynamicColorDescription,
                leading: const Icon(Icons.format_paint_outlined),
                value: settings.dynamicColor,
                onChanged: (value) =>
                    notifier.updateDynamicColor(value as bool),
              ),
            ],
          ),

        // --- Animations ---
        SettingsSection(
          title: l10n.settingsAnimationsSection,
          children: [
            if (disableAnimations)
              const Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: Spacing.md,
                  vertical: Spacing.xs,
                ),
                child: _SystemAnimationNote(),
              ),
            SettingsTile.info(
              key: const Key('tile_animations'),
              title: l10n.settingsReduceAnimations,
              subtitle: disableAnimations
                  ? l10n.settingsAnimationsDisabled
                  : l10n.settingsAnimationsEnabled,
              leading: const Icon(Icons.animation_outlined),
            ),
          ],
        ),

        // Bottom padding so content is not obscured by navigation bar.
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }

  // -- Helpers ---------------------------------------------------------------

  /// Whether to show the dynamic color toggle.
  ///
  /// Only visible when Material You theme is selected and the platform
  /// is Android (dynamic color requires Android 12+).
  bool _shouldShowDynamicColor(AppThemeMode themeMode) {
    if (themeMode != AppThemeMode.materialYou) return false;

    try {
      return Platform.isAndroid;
    } catch (e) {
      // Platform not available (e.g. in tests without platform override).
      return false;
    }
  }
}

// ---------------------------------------------------------------------------
// _ThemeModePicker
// ---------------------------------------------------------------------------

/// Displays theme mode options as preview thumbnail cards with radio selection.
class _ThemeModePicker extends StatelessWidget {
  const _ThemeModePicker({
    required this.selected,
    required this.onChanged,
  });

  final AppThemeMode selected;
  final ValueChanged<AppThemeMode> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Row(
      children: [
        Expanded(
          child: _ThemePreviewCard(
            key: const Key('theme_card_material_you'),
            label: l10n.settingsThemeMaterialYou,
            icon: Icons.auto_awesome_outlined,
            isSelected: selected == AppThemeMode.materialYou,
            previewColors: const _PreviewColors(
              background: Color(0xFFF5F5F5),
              primary: Color(0xFF6750A4),
              surface: Colors.white,
            ),
            onTap: () => onChanged(AppThemeMode.materialYou),
          ),
        ),
        const SizedBox(width: Spacing.md),
        Expanded(
          child: _ThemePreviewCard(
            key: const Key('theme_card_cyberpunk'),
            label: l10n.settingsThemeCyberpunk,
            icon: Icons.electric_bolt_outlined,
            isSelected: selected == AppThemeMode.cyberpunk,
            previewColors: const _PreviewColors(
              background: CyberColors.deepNavy,
              primary: CyberColors.matrixGreen,
              surface: CyberColors.darkBg,
            ),
            onTap: () => onChanged(AppThemeMode.cyberpunk),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// _PreviewColors
// ---------------------------------------------------------------------------

/// Color set for theme preview cards.
class _PreviewColors {
  const _PreviewColors({
    required this.background,
    required this.primary,
    required this.surface,
  });

  final Color background;
  final Color primary;
  final Color surface;
}

// ---------------------------------------------------------------------------
// _ThemePreviewCard
// ---------------------------------------------------------------------------

/// A selectable preview card displaying a miniature theme representation.
class _ThemePreviewCard extends StatelessWidget {
  const _ThemePreviewCard({
    super.key,
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.previewColors,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool isSelected;
  final _PreviewColors previewColors;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final borderColor = isSelected
        ? theme.colorScheme.primary
        : theme.colorScheme.outlineVariant;
    final borderWidth = isSelected ? 2.5 : 1.0;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: AnimDurations.fast,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(Radii.lg),
          border: Border.all(color: borderColor, width: borderWidth),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            // Preview thumbnail
            Container(
              height: 96,
              width: double.infinity,
              color: previewColors.background,
              child: _buildThumbnail(),
            ),

            // Label row
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: Spacing.sm,
                vertical: Spacing.sm,
              ),
              color: theme.colorScheme.surfaceContainerLow,
              child: Row(
                children: [
                  Icon(
                    isSelected
                        ? Icons.radio_button_checked
                        : Icons.radio_button_unchecked,
                    size: 20,
                    color: isSelected
                        ? theme.colorScheme.primary
                        : theme.colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: Spacing.xs),
                  Expanded(
                    child: Text(
                      label,
                      style: theme.textTheme.labelLarge?.copyWith(
                        fontWeight:
                            isSelected ? FontWeight.w600 : FontWeight.w400,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Builds a simplified preview of the theme inside the thumbnail area.
  Widget _buildThumbnail() {
    return Padding(
      padding: const EdgeInsets.all(Spacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Simulated app bar
          Container(
            height: 12,
            width: double.infinity,
            decoration: BoxDecoration(
              color: previewColors.primary,
              borderRadius: BorderRadius.circular(Radii.sm / 2),
            ),
          ),
          const SizedBox(height: Spacing.xs),
          // Simulated content card
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: previewColors.surface,
                borderRadius: BorderRadius.circular(Radii.sm / 2),
              ),
              child: Center(
                child: Icon(
                  icon,
                  size: 28,
                  color: previewColors.primary,
                ),
              ),
            ),
          ),
          const SizedBox(height: Spacing.xs),
          // Simulated bottom bar
          Row(
            children: List.generate(
              3,
              (index) => Expanded(
                child: Padding(
                  padding: EdgeInsets.only(
                    right: index < 2 ? Spacing.xs : 0,
                  ),
                  child: Container(
                    height: 6,
                    decoration: BoxDecoration(
                      color: index == 0
                          ? previewColors.primary
                          : previewColors.surface,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// _BrightnessSegmentedButton
// ---------------------------------------------------------------------------

/// Segmented button for selecting brightness preference.
class _BrightnessSegmentedButton extends StatelessWidget {
  const _BrightnessSegmentedButton({
    required this.selected,
    required this.onChanged,
  });

  final AppBrightness selected;
  final ValueChanged<AppBrightness> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return SizedBox(
      width: double.infinity,
      child: SegmentedButton<AppBrightness>(
        segments: [
          ButtonSegment(
            value: AppBrightness.system,
            label: Text(l10n.settingsThemeSystem),
            icon: const Icon(Icons.brightness_auto_outlined),
          ),
          ButtonSegment(
            value: AppBrightness.light,
            label: Text(l10n.settingsThemeLight),
            icon: const Icon(Icons.light_mode_outlined),
          ),
          ButtonSegment(
            value: AppBrightness.dark,
            label: Text(l10n.settingsThemeDark),
            icon: const Icon(Icons.dark_mode_outlined),
          ),
        ],
        selected: {selected},
        onSelectionChanged: (newSelection) {
          onChanged(newSelection.first);
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// _TextScalePicker
// ---------------------------------------------------------------------------

/// Picker for selecting text scale factor for accessibility.
class _TextScalePicker extends StatelessWidget {
  const _TextScalePicker({
    required this.selected,
    required this.onChanged,
  });

  final TextScale selected;
  final ValueChanged<TextScale> onChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Preview text
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(Spacing.md),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerLow,
            borderRadius: BorderRadius.circular(Radii.md),
          ),
          child: Text(
            l10n.settingsTextSizePreview,
            textAlign: TextAlign.center,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Scale options
        Wrap(
          spacing: Spacing.sm,
          runSpacing: Spacing.sm,
          children: TextScale.values.map((scale) {
            final isSelected = scale == selected;
            return ChoiceChip(
              key: Key('text_scale_${scale.name}'),
              label: Text(_textScaleLabel(l10n, scale)),
              selected: isSelected,
              onSelected: (_) => onChanged(scale),
            );
          }).toList(),
        ),
        const SizedBox(height: Spacing.sm),

        // Description
        Text(
          _textScaleDescription(l10n, selected),
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  String _textScaleLabel(AppLocalizations l10n, TextScale scale) {
    return switch (scale) {
      TextScale.system => l10n.settingsTextScaleSystem,
      TextScale.small => l10n.settingsTextScaleSmall,
      TextScale.normal => l10n.settingsTextScaleDefault,
      TextScale.large => l10n.settingsTextScaleLarge,
      TextScale.extraLarge => l10n.settingsTextScaleExtraLarge,
    };
  }

  String _textScaleDescription(AppLocalizations l10n, TextScale scale) {
    return switch (scale) {
      TextScale.system => l10n.settingsTextScaleSystemDescription,
      TextScale.small => l10n.settingsTextScaleSmallDescription,
      TextScale.normal => l10n.settingsTextScaleDefaultDescription,
      TextScale.large => l10n.settingsTextScaleLargeDescription,
      TextScale.extraLarge => l10n.settingsTextScaleExtraLargeDescription,
    };
  }
}

// ---------------------------------------------------------------------------
// _SystemAnimationNote
// ---------------------------------------------------------------------------

/// Info card shown when system animations are disabled.
class _SystemAnimationNote extends StatelessWidget {
  const _SystemAnimationNote();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(Spacing.sm),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(Radii.sm),
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline,
            size: 20,
            color: theme.colorScheme.onSecondaryContainer,
          ),
          const SizedBox(width: Spacing.sm),
          Expanded(
            child: Text(
              AppLocalizations.of(context).settingsAnimationsSystemDisabled,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
