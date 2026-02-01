import 'package:flutter/material.dart';

/// A reusable social login button with icon, label, loading state,
/// and error handling.
///
/// ```dart
/// SocialLoginButton(
///   icon: Icons.telegram,
///   label: 'Continue with Telegram',
///   onPressed: () async => launchTelegramAuth(),
///   isLoading: false,
/// )
/// ```
class SocialLoginButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final Color? backgroundColor;
  final Color? foregroundColor;

  const SocialLoginButton({
    super.key,
    required this.icon,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.backgroundColor,
    this.foregroundColor,
  });

  /// Convenience constructor for the Telegram login variant.
  factory SocialLoginButton.telegram({
    Key? key,
    required VoidCallback? onPressed,
    bool isLoading = false,
  }) {
    return SocialLoginButton(
      key: key,
      icon: Icons.telegram,
      label: 'Continue with Telegram',
      onPressed: onPressed,
      isLoading: isLoading,
      backgroundColor: const Color(0xFF0088CC),
      foregroundColor: Colors.white,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SizedBox(
      width: double.infinity,
      height: 52,
      child: OutlinedButton(
        onPressed: isLoading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          backgroundColor:
              backgroundColor ?? theme.colorScheme.surfaceContainerHighest,
          foregroundColor: foregroundColor ?? theme.colorScheme.onSurface,
          side: BorderSide(
            color: backgroundColor?.withValues(alpha: 0.6) ??
                theme.colorScheme.outline,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        ),
        child: isLoading
            ? SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: foregroundColor ?? theme.colorScheme.primary,
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 24),
                  const SizedBox(width: 12),
                  Text(
                    label,
                    style: theme.textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: foregroundColor,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
