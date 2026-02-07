import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';

// ---------------------------------------------------------------------------
// OnboardingState
// ---------------------------------------------------------------------------

/// Immutable state for the onboarding flow.
///
/// Holds the current page index, completion flag, and list of pages
/// returned from the [OnboardingRepository].
class OnboardingState {
  const OnboardingState({
    this.currentPage = 0,
    this.isComplete = false,
    this.pages = const [],
  });

  /// Zero-based index of the currently visible onboarding page.
  final int currentPage;

  /// Whether the user has completed (or skipped) onboarding.
  final bool isComplete;

  /// The ordered list of onboarding pages to display.
  final List<OnboardingPage> pages;

  /// Whether the user is on the last page.
  bool get isLastPage => pages.isNotEmpty && currentPage >= pages.length - 1;

  /// Whether the user is on the first page.
  bool get isFirstPage => currentPage <= 0;

  OnboardingState copyWith({
    int? currentPage,
    bool? isComplete,
    List<OnboardingPage>? pages,
  }) {
    return OnboardingState(
      currentPage: currentPage ?? this.currentPage,
      isComplete: isComplete ?? this.isComplete,
      pages: pages ?? this.pages,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is OnboardingState &&
        other.currentPage == currentPage &&
        other.isComplete == isComplete &&
        other.pages.length == pages.length;
  }

  @override
  int get hashCode => Object.hash(currentPage, isComplete, pages.length);

  @override
  String toString() =>
      'OnboardingState(currentPage: $currentPage, isComplete: $isComplete, '
      'pages: ${pages.length})';
}

// ---------------------------------------------------------------------------
// OnboardingNotifier
// ---------------------------------------------------------------------------

/// Manages the onboarding flow state with automatic persistence.
///
/// Loads the initial list of [OnboardingPage]s from [OnboardingRepository]
/// during [build] and provides navigation and completion methods.
class OnboardingNotifier extends AsyncNotifier<OnboardingState> {
  late final OnboardingRepository _repository;

  @override
  Future<OnboardingState> build() async {
    _repository = ref.watch(onboardingRepositoryProvider);

    final pages = await _repository.getPages();
    final hasCompleted = await _repository.hasCompletedOnboarding();

    return OnboardingState(
      currentPage: 0,
      isComplete: hasCompleted,
      pages: pages,
    );
  }

  // ── Navigation ──────────────────────────────────────────────────────────

  /// Advances to the next onboarding page if not already on the last page.
  void nextPage() {
    final current = state.value;
    if (current == null) return;
    if (current.isLastPage) return;

    state = AsyncData(
      current.copyWith(currentPage: current.currentPage + 1),
    );
    AppLogger.debug('Onboarding: moved to page ${current.currentPage + 1}');
  }

  /// Returns to the previous onboarding page if not already on the first page.
  void previousPage() {
    final current = state.value;
    if (current == null) return;
    if (current.isFirstPage) return;

    state = AsyncData(
      current.copyWith(currentPage: current.currentPage - 1),
    );
    AppLogger.debug('Onboarding: moved to page ${current.currentPage - 1}');
  }

  // ── Completion ──────────────────────────────────────────────────────────

  /// Skips the remaining onboarding pages and marks onboarding as complete.
  ///
  /// Persists the completion flag via [OnboardingRepository.completeOnboarding].
  Future<void> skip() async {
    try {
      await _repository.completeOnboarding();
      final current = state.value;
      if (current == null) return;

      state = AsyncData(current.copyWith(isComplete: true));
      ref.invalidate(shouldShowOnboardingProvider);
      AppLogger.info('Onboarding: skipped');
    } catch (e, st) {
      AppLogger.error('Failed to skip onboarding', error: e, stackTrace: st);
      rethrow;
    }
  }

  /// Completes onboarding (typically called from the last page CTA).
  ///
  /// Persists the completion flag via [OnboardingRepository.completeOnboarding].
  Future<void> complete() async {
    try {
      await _repository.completeOnboarding();
      final current = state.value;
      if (current == null) return;

      state = AsyncData(current.copyWith(isComplete: true));
      ref.invalidate(shouldShowOnboardingProvider);
      AppLogger.info('Onboarding: completed');
    } catch (e, st) {
      AppLogger.error(
        'Failed to complete onboarding',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }
}

// ---------------------------------------------------------------------------
// Main provider
// ---------------------------------------------------------------------------

/// Provides the [OnboardingNotifier] managing [OnboardingState].
final onboardingProvider =
    AsyncNotifierProvider<OnboardingNotifier, OnboardingState>(
  OnboardingNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether the onboarding flow should be shown to the user.
///
/// Returns `true` when onboarding has **not** been completed yet,
/// `false` after the user has completed or skipped onboarding.
///
/// This provider performs an async check against the repository so that
/// the app can decide at startup whether to show the onboarding screen.
final shouldShowOnboardingProvider = FutureProvider<bool>((ref) async {
  final repository = ref.watch(onboardingRepositoryProvider);
  final hasCompleted = await repository.hasCompletedOnboarding();
  return !hasCompleted;
});
