import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/security/data/datasources/security_remote_ds.dart';
import 'package:cybervpn_mobile/features/security/data/repositories/security_repository_impl.dart';
import 'package:cybervpn_mobile/features/security/domain/entities/antiphishing_code.dart';
import 'package:cybervpn_mobile/features/security/domain/repositories/security_repository.dart';

// ── Repository Providers ──────────────────────────────────────────────────

/// Provides the [SecurityRemoteDataSource] instance.
final securityRemoteDataSourceProvider = Provider<SecurityRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SecurityRemoteDataSource(apiClient);
});

/// Provides the [SecurityRepository] implementation.
final securityRepositoryProvider = Provider<SecurityRepository>((ref) {
  final remoteDataSource = ref.watch(securityRemoteDataSourceProvider);
  return SecurityRepositoryImpl(remoteDataSource);
});

// ── State Providers ───────────────────────────────────────────────────────

/// Provides the user's current antiphishing code.
///
/// This provider fetches the code from the backend when accessed.
/// Use [.autoDispose] to clean up when the screen is disposed.
final antiphishingCodeProvider =
    FutureProvider.autoDispose<AntiphishingCode>((ref) async {
  final repository = ref.watch(securityRepositoryProvider);
  final result = await repository.getAntiphishingCode();

  // Extract data or provide default value with null code
  return result.dataOrNull ?? const AntiphishingCode(code: null);
});
