import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';

/// A reusable settings tile with multiple variants: navigation, toggle, radio.
///
/// Use the named constructors to create the appropriate variant:
///
/// ```dart
/// SettingsTile.navigation(
///   title: 'Language',
///   subtitle: 'English',
///   onTap: () => navigateToLanguage(),
/// )
///
/// SettingsTile.toggle(
///   title: 'Dark Mode',
///   value: isDark,
///   onChanged: (v) => setDarkMode(v),
/// )
///
/// SettingsTile.radio(
///   title: 'VLESS-Reality',
///   value: 'vless-reality',
///   groupValue: selectedProtocol,
///   onChanged: (v) => selectProtocol(v),
/// )
/// ```
class SettingsTile extends ConsumerWidget {
  // ---------------------------------------------------------------------------
  // Navigation variant
  // ---------------------------------------------------------------------------

  /// Creates a navigation-style settings tile with a trailing chevron.
  ///
  /// Tapping the tile triggers [onTap].
  const SettingsTile.navigation({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
    required VoidCallback this.onTap,
  })  : _variant = _SettingsTileVariant.navigation,
        value = null,
        groupValue = null,
        onChanged = null;

  // ---------------------------------------------------------------------------
  // Toggle variant
  // ---------------------------------------------------------------------------

  /// Creates a toggle-style settings tile with a trailing [Switch].
  ///
  /// The entire tile is tappable and triggers [onChanged] with the toggled
  /// boolean value.
  const SettingsTile.toggle({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
    required bool this.value,
    required this.onChanged,
  })  : _variant = _SettingsTileVariant.toggle,
        groupValue = null,
        onTap = null;

  // ---------------------------------------------------------------------------
  // Radio variant
  // ---------------------------------------------------------------------------

  /// Creates a radio-style settings tile with a trailing [Radio].
  ///
  /// The tile is selected when [value] equals [groupValue]. Tapping the
  /// tile triggers [onChanged] with [value].
  const SettingsTile.radio({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
    required this.value,
    required this.groupValue,
    required this.onChanged,
  })  : _variant = _SettingsTileVariant.radio,
        onTap = null;

  // ---------------------------------------------------------------------------
  // Info variant
  // ---------------------------------------------------------------------------

  /// Creates a display-only settings tile with no trailing action.
  ///
  /// Use this for tiles that show a current value but are not interactive.
  const SettingsTile.info({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
  })  : _variant = _SettingsTileVariant.info,
        value = null,
        groupValue = null,
        onChanged = null,
        onTap = null;

  // ---------------------------------------------------------------------------
  // Fields
  // ---------------------------------------------------------------------------

  /// The primary text displayed on the tile.
  final String title;

  /// Optional secondary text below [title].
  final String? subtitle;

  /// Optional leading widget (e.g. an icon).
  final Widget? leading;

  /// Callback for navigation tiles.
  final VoidCallback? onTap;

  /// Current value -- boolean for toggle, selection value for radio.
  final dynamic value;

  /// The currently selected group value for radio tiles.
  final dynamic groupValue;

  /// Callback when the value changes (toggle or radio).
  final ValueChanged<dynamic>? onChanged;

  /// Internal variant discriminator.
  final _SettingsTileVariant _variant;

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final titleStyle = theme.textTheme.bodyLarge?.copyWith(
      color: colorScheme.onSurface,
    );

    final subtitleStyle = theme.textTheme.bodySmall?.copyWith(
      color: colorScheme.onSurfaceVariant,
    );

    return switch (_variant) {
      _SettingsTileVariant.navigation => _buildNavigation(
          titleStyle: titleStyle,
          subtitleStyle: subtitleStyle,
          colorScheme: colorScheme,
        ),
      _SettingsTileVariant.toggle => _buildToggle(
          ref: ref,
          titleStyle: titleStyle,
          subtitleStyle: subtitleStyle,
        ),
      _SettingsTileVariant.radio => _buildRadio(
          titleStyle: titleStyle,
          subtitleStyle: subtitleStyle,
          colorScheme: colorScheme,
        ),
      _SettingsTileVariant.info => _buildInfo(
          titleStyle: titleStyle,
          subtitleStyle: subtitleStyle,
        ),
    };
  }

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  Widget _buildNavigation({
    required TextStyle? titleStyle,
    required TextStyle? subtitleStyle,
    required ColorScheme colorScheme,
  }) {
    return Semantics(
      label: '$title${subtitle != null ? ', $subtitle' : ''}',
      button: true,
      hint: 'Tap to open $title settings',
      child: ListTile(
        leading: leading,
        title: Text(title, style: titleStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle:
            subtitle != null ? Text(subtitle!, style: subtitleStyle, maxLines: 1, overflow: TextOverflow.ellipsis) : null,
        trailing: ExcludeSemantics(
          child: Icon(
            Icons.chevron_right,
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        onTap: onTap,
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Toggle
  // ---------------------------------------------------------------------------

  Widget _buildToggle({
    required WidgetRef ref,
    required TextStyle? titleStyle,
    required TextStyle? subtitleStyle,
  }) {
    final bool currentValue = value as bool;

    void handleToggle(bool newValue) {
      // Trigger haptic feedback on toggle.
      final haptics = ref.read(hapticServiceProvider);
      unawaited(haptics.selection());

      onChanged?.call(newValue);
    }

    final semanticLabel = '$title, ${currentValue ? 'enabled' : 'disabled'}';

    return Semantics(
      label: semanticLabel,
      toggled: currentValue,
      hint: 'Tap to ${currentValue ? 'disable' : 'enable'} $title',
      child: ListTile(
        leading: leading,
        title: Text(title, style: titleStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle:
            subtitle != null ? Text(subtitle!, style: subtitleStyle, maxLines: 1, overflow: TextOverflow.ellipsis) : null,
        trailing: Switch(
          value: currentValue,
          onChanged: handleToggle,
        ),
        onTap: () => handleToggle(!currentValue),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Radio
  // ---------------------------------------------------------------------------

  Widget _buildRadio({
    required TextStyle? titleStyle,
    required TextStyle? subtitleStyle,
    required ColorScheme colorScheme,
  }) {
    final bool isSelected = value == groupValue;

    final semanticLabel = '$title${isSelected ? ', selected' : ''}';

    return Semantics(
      label: semanticLabel,
      selected: isSelected,
      button: true,
      hint: 'Tap to select $title',
      child: RadioGroup<dynamic>(
        groupValue: groupValue,
        onChanged: (dynamic newValue) => onChanged?.call(newValue),
        child: ListTile(
          leading: leading,
          title: Text(title, style: titleStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle:
              subtitle != null ? Text(subtitle!, style: subtitleStyle, maxLines: 1, overflow: TextOverflow.ellipsis) : null,
          trailing: Radio<dynamic>(
            value: value,
            toggleable: false,
          ),
          onTap: () => onChanged?.call(value),
          selected: isSelected,
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Info
  // ---------------------------------------------------------------------------

  Widget _buildInfo({
    required TextStyle? titleStyle,
    required TextStyle? subtitleStyle,
  }) {
    return Semantics(
      label: '$title${subtitle != null ? ', $subtitle' : ''}',
      hint: 'Displays $title information',
      readOnly: true,
      child: ListTile(
        leading: leading,
        title: Text(title, style: titleStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: subtitle != null ? Text(subtitle!, style: subtitleStyle, maxLines: 1, overflow: TextOverflow.ellipsis) : null,
      ),
    );
  }
}

/// Internal enum to discriminate between tile variants.
enum _SettingsTileVariant {
  navigation,
  toggle,
  radio,
  info,
}
