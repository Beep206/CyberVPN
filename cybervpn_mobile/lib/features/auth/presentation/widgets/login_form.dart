import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/utils/input_validators.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';

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
    if (!(_formKey.currentState?.validate() ?? false)) return;

    await ref.read(authProvider.notifier).login(
          _emailController.text.trim(),
          _passwordController.text,
          rememberMe: _rememberMe,
        );

    if (!mounted) return;

    final authState = ref.read(authProvider).value;

    if (authState is AuthError) {
      _passwordController.clear();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(authState.message),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else if (authState is AuthAuthenticated) {
      widget.onSuccess?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
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
            FocusTraversalOrder(
              order: const NumericFocusOrder(1),
              child: TextFormField(
                controller: _emailController,
                enabled: !isLoading,
                autofocus: true,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.email],
                decoration: const InputDecoration(
                  labelText: 'Email',
                  hintText: 'Enter your email',
                  prefixIcon: Icon(
                    Icons.email_outlined,
                    semanticLabel: '', // Hide from screen reader (label is sufficient)
                  ),
                ),
                validator: InputValidators.validateEmail,
                autovalidateMode: AutovalidateMode.onUserInteraction,
              ),
            ),
          const SizedBox(height: 16),

          // Password field
          FocusTraversalOrder(
            order: const NumericFocusOrder(2),
            child: TextFormField(
              controller: _passwordController,
              enabled: !isLoading,
              obscureText: _obscurePassword,
              textInputAction: TextInputAction.done,
              autofillHints: const [AutofillHints.password],
              decoration: InputDecoration(
                labelText: 'Password',
                hintText: 'Enter your password',
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
                  tooltip: _obscurePassword ? 'Show password' : 'Hide password',
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
                child: Text('Remember me', style: theme.textTheme.bodyMedium),
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
                      'Forgot password?',
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

          // Login button
          FocusTraversalOrder(
            order: const NumericFocusOrder(5),
            child: Semantics(
              button: true,
              enabled: !isLoading,
              label: isLoading ? 'Signing in, please wait' : 'Login',
              hint: 'Sign in to your account',
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
                      : const ExcludeSemantics(child: Text('Login')),
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
