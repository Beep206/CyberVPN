import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

/// Test screen to preview all Lottie animations.
/// This screen is for development/testing purposes only.
class AnimationPreviewScreen extends StatelessWidget {
  const AnimationPreviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Lottie Animation Preview'),
        backgroundColor: const Color(0xFF00ff88),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildAnimationCard(
            context,
            'Onboarding Privacy',
            'assets/animations/onboarding_privacy.json',
          ),
          _buildAnimationCard(
            context,
            'Onboarding Connect',
            'assets/animations/onboarding_connect.json',
          ),
          _buildAnimationCard(
            context,
            'Onboarding Globe',
            'assets/animations/onboarding_globe.json',
          ),
          _buildAnimationCard(
            context,
            'Connecting',
            'assets/animations/connecting.json',
          ),
          _buildAnimationCard(
            context,
            'Connected Success',
            'assets/animations/connected_success.json',
          ),
          _buildAnimationCard(
            context,
            'Speed Test',
            'assets/animations/speed_test.json',
          ),
          _buildAnimationCard(
            context,
            'Empty State',
            'assets/animations/empty_state.json',
          ),
          _buildAnimationCard(
            context,
            'Privacy (onboarding alt)',
            'assets/animations/privacy.json',
          ),
          _buildAnimationCard(
            context,
            'Connect (onboarding alt)',
            'assets/animations/connect.json',
          ),
          _buildAnimationCard(
            context,
            'Globe (onboarding alt)',
            'assets/animations/globe.json',
          ),
          _buildAnimationCard(
            context,
            'Get Started',
            'assets/animations/get_started.json',
          ),
        ],
      ),
    );
  }

  Widget _buildAnimationCard(
    BuildContext context,
    String title,
    String assetPath,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              assetPath,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 16),
            Center(
              child: SizedBox(
                width: 200,
                height: 200,
                child: Lottie.asset(
                  assetPath,
                  fit: BoxFit.contain,
                  repeat: true,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      color: Colors.red[100],
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error, color: Colors.red),
                            const SizedBox(height: 8),
                            Text(
                              'Error loading animation',
                              style: TextStyle(color: Colors.red[900]),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
