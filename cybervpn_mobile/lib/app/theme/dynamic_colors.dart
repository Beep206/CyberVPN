import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// ---------------------------------------------------------------------------
// Dynamic color schemes provider (fed by DynamicColorBuilder in app.dart)
// ---------------------------------------------------------------------------

/// Holds the dynamic color schemes provided by the platform on Android 12+.
///
/// Updated from [DynamicColorBuilder] in the widget tree.  When the platform
/// does not support dynamic colors both fields will be `null`.
class DynamicColorSchemes {
  const DynamicColorSchemes({this.light, this.dark});

  /// Light dynamic [ColorScheme] from the user's wallpaper, or `null`.
  final ColorScheme? light;

  /// Dark dynamic [ColorScheme] from the user's wallpaper, or `null`.
  final ColorScheme? dark;

  /// Whether the platform provided dynamic color schemes.
  bool get hasDynamicColors => light != null && dark != null;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DynamicColorSchemes &&
          runtimeType == other.runtimeType &&
          light == other.light &&
          dark == other.dark;

  @override
  int get hashCode => Object.hash(light, dark);
}

/// Notifier that stores the dynamic color schemes obtained from
/// [DynamicColorBuilder].
///
/// Call [update] from the builder callback to push new schemes into the
/// Riverpod state graph.
class DynamicColorNotifier extends Notifier<DynamicColorSchemes> {
  @override
  DynamicColorSchemes build() => const DynamicColorSchemes();

  /// Updates the cached dynamic color schemes.
  void update({ColorScheme? light, ColorScheme? dark}) {
    final next = DynamicColorSchemes(light: light, dark: dark);
    if (state != next) {
      state = next;
    }
  }
}

/// Provides the current [DynamicColorSchemes] from the platform.
///
/// Downstream providers (e.g. [currentThemeDataProvider]) watch this to
/// reactively rebuild when the user changes their wallpaper on Android 12+.
final dynamicColorProvider =
    NotifierProvider<DynamicColorNotifier, DynamicColorSchemes>(
  DynamicColorNotifier.new,
);
