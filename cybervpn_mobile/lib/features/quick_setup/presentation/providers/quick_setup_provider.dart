import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Storage key
// ---------------------------------------------------------------------------

const _quickSetupCompletedKey = 'quick_setup_completed';
const _quickSetupAbandonedKey = 'quick_setup_abandoned';

// ---------------------------------------------------------------------------
// Quick Setup State
// ---------------------------------------------------------------------------

/// Immutable state for quick setup flow.
class QuickSetupState {
  const QuickSetupState({
    this.completed = false,
    this.abandoned = false,
    this.isConnecting = false,
    this.error,
  });

  final bool completed;
  final bool abandoned;
  final bool isConnecting;
  final String? error;

  QuickSetupState copyWith({
    bool? completed,
    bool? abandoned,
    bool? isConnecting,
    String? Function()? error,
  }) {
    return QuickSetupState(
      completed: completed ?? this.completed,
      abandoned: abandoned ?? this.abandoned,
      isConnecting: isConnecting ?? this.isConnecting,
      error: error != null ? error() : this.error,
    );
  }
}

// ---------------------------------------------------------------------------
// QuickSetupNotifier
// ---------------------------------------------------------------------------

class QuickSetupNotifier extends AsyncNotifier<QuickSetupState> {
  late final SharedPreferences _prefs;

  @override
  Future<QuickSetupState> build() async {
    _prefs = ref.watch(sharedPreferencesProvider);
    final completed = _prefs.getBool(_quickSetupCompletedKey) ?? false;
    final abandoned = _prefs.getBool(_quickSetupAbandonedKey) ?? false;
    return QuickSetupState(completed: completed, abandoned: abandoned);
  }

  /// Check if quick setup has been completed before.
  bool get isCompleted => state.value?.completed ?? false;

  /// Mark quick setup as completed and persist the flag.
  Future<void> complete() async {
    try {
      await _prefs.setBool(_quickSetupCompletedKey, true);
      state = AsyncData(
        (state.value ?? const QuickSetupState()).copyWith(completed: true),
      );
      AppLogger.info('Quick setup marked as completed');
    } catch (e, st) {
      AppLogger.error('Failed to mark quick setup as completed',
          error: e, stackTrace: st);
    }
  }

  /// Set the connecting state during the first connection attempt.
  void setConnecting(bool isConnecting) {
    final current = state.value ?? const QuickSetupState();
    state = AsyncData(current.copyWith(isConnecting: isConnecting));
  }

  /// Set an error message.
  void setError(String? error) {
    final current = state.value ?? const QuickSetupState();
    state = AsyncData(current.copyWith(error: () => error));
  }

  /// Mark quick setup as abandoned (timeout or user skipped).
  Future<void> abandon() async {
    try {
      await _prefs.setBool(_quickSetupAbandonedKey, true);
      await _prefs.setBool(_quickSetupCompletedKey, true);
      state = AsyncData(
        (state.value ?? const QuickSetupState()).copyWith(
          abandoned: true,
          completed: true,
        ),
      );
      AppLogger.info('Quick setup marked as abandoned');
    } catch (e, st) {
      AppLogger.error('Failed to mark quick setup as abandoned',
          error: e, stackTrace: st);
    }
  }

  /// Resume quick setup (allow user to retry from settings).
  Future<void> resume() async {
    try {
      await _prefs.remove(_quickSetupCompletedKey);
      await _prefs.remove(_quickSetupAbandonedKey);
      state = const AsyncData(QuickSetupState());
      AppLogger.info('Quick setup resumed - flags cleared');
    } catch (e, st) {
      AppLogger.error('Failed to resume quick setup',
          error: e, stackTrace: st);
    }
  }

  /// Reset the quick setup state (for testing or re-onboarding scenarios).
  Future<void> reset() async {
    try {
      await _prefs.remove(_quickSetupCompletedKey);
      await _prefs.remove(_quickSetupAbandonedKey);
      state = const AsyncData(QuickSetupState());
      AppLogger.info('Quick setup state reset');
    } catch (e, st) {
      AppLogger.error('Failed to reset quick setup state',
          error: e, stackTrace: st);
    }
  }
}

// ---------------------------------------------------------------------------
// Dependency providers
// ---------------------------------------------------------------------------

/// Provider for [SharedPreferences]. Must be overridden in DI setup.
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError(
    'sharedPreferencesProvider must be overridden with a SharedPreferences '
    'instance in a ProviderScope.',
  );
});

// ---------------------------------------------------------------------------
// Main provider
// ---------------------------------------------------------------------------

final quickSetupProvider =
    AsyncNotifierProvider<QuickSetupNotifier, QuickSetupState>(
  QuickSetupNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether the user should see the quick setup flow (first time authenticated).
final shouldShowQuickSetupProvider = Provider<bool>((ref) {
  final quickSetup = ref.watch(quickSetupProvider).value;
  return !(quickSetup?.completed ?? false);
});
