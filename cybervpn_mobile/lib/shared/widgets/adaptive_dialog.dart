import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Describes a single action button inside an [AdaptiveDialog].
class AdaptiveDialogAction {
  /// The text label displayed on the action button.
  final String label;

  /// Callback invoked when the action is tapped.
  ///
  /// If `null` the action will only dismiss the dialog.
  final VoidCallback? onPressed;

  /// Whether this action represents a destructive operation (e.g. delete).
  ///
  /// On iOS this renders the button in red using
  /// [CupertinoDialogAction.isDestructiveAction].
  /// On Android the text color is set to [ColorScheme.error].
  final bool isDestructive;

  const AdaptiveDialogAction({
    required this.label,
    this.onPressed,
    this.isDestructive = false,
  });
}

/// A platform-adaptive alert dialog that renders [CupertinoAlertDialog] on iOS
/// and [AlertDialog] on Android (and other platforms).
///
/// Use the static [AdaptiveDialog.show] method to present the dialog.
///
/// Example:
/// ```dart
/// AdaptiveDialog.show(
///   context: context,
///   title: 'Delete Server',
///   content: 'Are you sure you want to remove this server?',
///   actions: [
///     AdaptiveDialogAction(label: 'Cancel'),
///     AdaptiveDialogAction(
///       label: 'Delete',
///       isDestructive: true,
///       onPressed: () => ref.read(serversProvider.notifier).delete(id),
///     ),
///   ],
/// );
/// ```
class AdaptiveDialog extends StatelessWidget {
  /// The title displayed at the top of the dialog.
  final String title;

  /// The body text displayed below the title.
  final String content;

  /// The action buttons shown at the bottom of the dialog.
  ///
  /// Each action automatically dismisses the dialog before invoking its
  /// [AdaptiveDialogAction.onPressed] callback.
  final List<AdaptiveDialogAction> actions;

  const AdaptiveDialog({
    super.key,
    required this.title,
    required this.content,
    required this.actions,
  });

  /// Presents the dialog using the appropriate platform style.
  ///
  /// Returns a [Future] that completes when the dialog is dismissed.
  static Future<void> show({
    required BuildContext context,
    required String title,
    required String content,
    required List<AdaptiveDialogAction> actions,
  }) {
    return showDialog<void>(
      context: context,
      builder: (_) => AdaptiveDialog(
        title: title,
        content: content,
        actions: actions,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final platform = Theme.of(context).platform;

    if (platform == TargetPlatform.iOS) {
      return _buildCupertinoDialog(context);
    }

    return _buildMaterialDialog(context);
  }

  // ---------------------------------------------------------------------------
  // iOS
  // ---------------------------------------------------------------------------

  Widget _buildCupertinoDialog(BuildContext context) {
    return CupertinoAlertDialog(
      title: Text(title),
      content: Text(content),
      actions: actions.map((action) {
        return CupertinoDialogAction(
          isDestructiveAction: action.isDestructive,
          onPressed: () {
            Navigator.of(context).pop();
            action.onPressed?.call();
          },
          child: Text(action.label),
        );
      }).toList(),
    );
  }

  // ---------------------------------------------------------------------------
  // Android / other
  // ---------------------------------------------------------------------------

  Widget _buildMaterialDialog(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: Text(title),
      content: Text(content),
      actions: actions.map((action) {
        return TextButton(
          onPressed: () {
            Navigator.of(context).pop();
            action.onPressed?.call();
          },
          child: Text(
            action.label,
            style: action.isDestructive
                ? TextStyle(color: theme.colorScheme.error)
                : null,
          ),
        );
      }).toList(),
    );
  }
}
