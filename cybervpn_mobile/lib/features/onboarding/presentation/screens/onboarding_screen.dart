import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/providers/onboarding_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/onboarding_page_widget.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/page_indicator.dart';

/// Full-screen onboarding carousel displayed on first launch.
///
/// Contains 4 swipeable pages with placeholder icons, a page indicator,
/// a Skip button (pages 0-2), and a Get Started button (page 3).
/// On completion or skip, the user is navigated to the auth screen.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  late final PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onPageChanged(int index) {
    final state = ref.read(onboardingProvider).value;
    if (state == null) return;

    // Sync the provider state with the PageView.
    if (index > state.currentPage) {
      for (var i = state.currentPage; i < index; i++) {
        ref.read(onboardingProvider.notifier).nextPage();
      }
    } else if (index < state.currentPage) {
      for (var i = state.currentPage; i > index; i--) {
        ref.read(onboardingProvider.notifier).previousPage();
      }
    }
  }

  Future<void> _handleSkip() async {
    await ref.read(onboardingProvider.notifier).skip();
    if (mounted) {
      context.go('/permissions');
    }
  }

  Future<void> _handleGetStarted() async {
    await ref.read(onboardingProvider.notifier).complete();
    if (mounted) {
      context.go('/permissions');
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(onboardingProvider);

    return Scaffold(
      body: SafeArea(
        child: asyncState.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(child: Text('Error: $error')),
          data: (state) => _buildContent(context, state),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, OnboardingState state) {
    final pages = state.pages;
    if (pages.isEmpty) {
      return const Center(child: Text('No onboarding pages'));
    }

    return Column(
      children: [
        // -- Skip button (top-right, visible on pages 0 through N-2) --
        Align(
          alignment: Alignment.topRight,
          child: Padding(
            padding: const EdgeInsets.only(
              top: Spacing.sm,
              right: Spacing.md,
            ),
            child: AnimatedOpacity(
              opacity: state.isLastPage ? 0.0 : 1.0,
              duration: AnimDurations.normal,
              child: IgnorePointer(
                ignoring: state.isLastPage,
                child: TextButton(
                  onPressed: _handleSkip,
                  child: const Text('Skip'),
                ),
              ),
            ),
          ),
        ),

        // -- Page content --
        Expanded(
          child: PageView.builder(
            controller: _pageController,
            itemCount: pages.length,
            onPageChanged: _onPageChanged,
            itemBuilder: (context, index) {
              return OnboardingPageWidget(
                page: pages[index],
                pageIndex: index,
              );
            },
          ),
        ),

        // -- Bottom controls --
        Padding(
          padding: const EdgeInsets.only(
            bottom: Spacing.xl,
            left: Spacing.xl,
            right: Spacing.xl,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Page indicator dots
              PageIndicator(
                pageCount: pages.length,
                currentPage: state.currentPage,
              ),
              const SizedBox(height: Spacing.lg),

              // Get Started button (visible only on last page)
              AnimatedSwitcher(
                duration: AnimDurations.normal,
                child: state.isLastPage
                    ? SizedBox(
                        key: const ValueKey('get-started'),
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _handleGetStarted,
                          child: const Text('Get Started'),
                        ),
                      )
                    : const SizedBox(
                        key: ValueKey('spacer'),
                        height: 48,
                      ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
