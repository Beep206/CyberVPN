import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/review/data/services/review_service.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart'
    show sharedPreferencesProvider;

/// Provides the [ReviewService] instance.
///
/// Depends on [sharedPreferencesProvider] for persistence.
final reviewServiceProvider = Provider<ReviewService>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return ReviewService(prefs: prefs);
});
