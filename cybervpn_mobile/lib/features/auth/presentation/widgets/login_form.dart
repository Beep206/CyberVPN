import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/input_validators.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/shared/widgets/animated_form_field.dart';

/// Extracted login form widget that manages its own controllers and
/// validation state.
///
/// Calls [authProvider]'s `login` method on submit and disables all
/// fields while a request is in-flight. Clears the password field on
/// authentication errors.
class LoginForm extends ConsumerStatefulWidget {
  /// Optional callback invoked after a successful login.
  final VoidCallback? onSuccess;

  /// Whether the "Remember me" checkbox is initially checked.
  final bool initialRememberMe;

  /// Callback when "Forgot password?" is tapped.
  final VoidCallback? onForgotPassword;

  const LoginForm({
    super.key,
    this.onSuccess,
    this.initialRememberMe = false,
    this.onForgotPassword,
  });

  @override
  ConsumerState<LoginForm> createState() => _LoginFormState();
}

class _LoginFormState extends ConsumerState<LoginForm> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _obscurePassword = true;
  bool _rememberMe = false;
  bool _shakeFields = false;
  bool _showSuccess = false;

  @override
  void initState() {
    super.initState();
    _rememberMe = widget.initialRememberMe;
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _onSubmit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      // Trigger shake animation on validation failure.
      setState(() => _shakeFields = true);
      Future.delayed(const Duration(milliseconds: 350), () {
        if (mounted) setState(() => _shakeFields = false);
      });
      return;
    }

    // Trigger light haptic on button tap.
    unawaited(ref.read(hapticServiceProvider).selection());

    await ref.read(authProvider.notifier).login(
          _emailController.text.trim(),
          _passwordController.text,
          rememberMe: _rememberMe,
        );

    if (!mounted) return;

    final authState = ref.read(authProvider).value;

    switch (authState) {
      case AuthError(:final message):
        _passwordController.clear();
        if (!mounted) return;

        // Shake fields on auth error.
        setState(() => _shakeFields = true);
        Future.delayed(const Duration(milliseconds: 350), () {
          if (mounted) setState(() => _shakeFields = false);
        });

        // Trigger error haptic when showing error SnackBar.
        final haptics = ref.read(hapticServiceProvider);
        unawaited(haptics.error());

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Theme.of(context).colorScheme.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
      case AuthAuthenticated():
        // Show brief success animation before navigating.
        setState(() => _showSuccess = true);
        widget.onSuccess?.call();
      default:
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final authAsync = ref.watch(authProvider);
    final authState = authAsync.value;
    final isLoading = authState is AuthLoading;

    return FocusTraversalGroup(
      policy: OrderedTraversalPolicy(),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Email field
            ShakeWidget(
              shake: _shakeFields,
              child: AnimatedFormField(
                child: FocusTraversalOrder(
                  order: const NumericFocusOrder(1),
                  child: TextFormField(
                    controller: _emailController,
                    enabled: !isLoading,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.email],
                    decoration: InputDecoration(
                      labelText: l10n.formEmailLabel,
                      hintText: l10n.formEmailHint,
                      prefixIcon: Icon(
                        Icons.email_outlined,
                        semanticLabel: '', // Hide from screen reader (label is sufficient)
                      ),
                    ),
                    validator: InputValidators.validateEmail,
                    autovalidateMode: AutovalidateMode.onUserInteraction,
                  ),
                ),
              ),
            ),
          const SizedBox(height: 16),

          // Password field
          ShakeWidget(
            shake: _shakeFields,
            child: AnimatedFormField(
              child: FocusTraversalOrder(
                order: const NumericFocusOrder(2),
                child: TextFormField(
                  controller: _passwordController,
                  enabled: !isLoading,
                  obscureText: _obscurePassword,
                  textInputAction: TextInputAction.done,
                  autofillHints: const [AutofillHints.password],
                  decoration: InputDecoration(
                    labelText: l10n.formPasswordLabel,
                    hintText: l10n.formPasswordHint,
                    prefixIcon: const Icon(
                      Icons.lock_outlined,
                      semanticLabel: '', // Hide from screen reader
                    ),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        semanticLabel: '', // Handled by tooltip
                      ),
                      tooltip: _obscurePassword ? l10n.formShowPassword : l10n.formHidePassword,
                      onPressed: isLoading
                          ? null
                          : () =>
                              setState(() => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                  validator: InputValidators.validatePassword,
                  autovalidateMode: AutovalidateMode.onUserInteraction,
                  onFieldSubmitted: (_) => _onSubmit(),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),

          // Remember me + Forgot password row
          Row(
            children: [
              FocusTraversalOrder(
                order: const NumericFocusOrder(3),
                child: Semantics(
                  label: 'Remember me',
                  hint: 'Keep me signed in on this device',
                  child: SizedBox(
                    height: 24,
                    width: 24,
                    child: Checkbox(
                      value: _rememberMe,
                      onChanged: isLoading
                          ? null
                          : (v) => setState(() => _rememberMe = v ?? false),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              ExcludeSemantics(
                child: Text(l10n.loginRememberMe, style: theme.textTheme.bodyMedium),
              ),
              const Spacer(),
              FocusTraversalOrder(
                order: const NumericFocusOrder(4),
                child: Semantics(
                  button: true,
                  hint: 'Opens password recovery',
                  child: TextButton(
                    onPressed: isLoading ? null : widget.onForgotPassword,
                    child: Text(
                      l10n.forgotPassword,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Login button with success overlay
          FocusTraversalOrder(
            order: const NumericFocusOrder(5),
            child: _showSuccess
                ? const SizedBox(
                    height: 52,
                    child: Center(child: SuccessCheckmark()),
                  )
                : Semantics(
                    button: true,
                    enabled: !isLoading,
                    label: isLoading ? l10n.loginSigningIn : l10n.loginButton,
                    hint: l10n.loginHint,
                    child: SizedBox(
                      height: 52,
                      child: ElevatedButton(
                        onPressed: isLoading ? null : _onSubmit,
                        child: isLoading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2.5),
                              )
                            : ExcludeSemantics(child: Text(l10n.loginButton)),
                      ),
                    ),
                  ),
          ),
        ],
        ),
      ),
    );
  }
}
