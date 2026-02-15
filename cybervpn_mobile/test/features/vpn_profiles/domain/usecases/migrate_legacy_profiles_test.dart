import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/migrate_legacy_profiles.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockVpnProfileRepository extends Mock implements ProfileRepository {}

void main() {
  late MigrateLegacyProfilesUseCase useCase;
  late MockVpnProfileRepository mockRepository;

  setUp(() {
    mockRepository = MockVpnProfileRepository();
    useCase = MigrateLegacyProfilesUseCase(mockRepository);
  });

  group('MigrateLegacyProfilesUseCase', () {
    test('returns Success when migration completes', () async {
      when(() => mockRepository.migrateFromLegacy())
          .thenAnswer((_) async => const Success(null));

      final result = await useCase();

      expect(result, isA<Success<void>>());
      verify(() => mockRepository.migrateFromLegacy()).called(1);
    });

    test('returns Failure when migration fails', () async {
      when(() => mockRepository.migrateFromLegacy())
          .thenAnswer((_) async =>
              const Failure(CacheFailure(message: 'Migration failed')));

      final result = await useCase();

      expect(result.isFailure, true);
      final failure = (result as Failure<void>).failure;
      expect(failure, isA<CacheFailure>());
      expect(failure.message, 'Migration failed');
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.migrateFromLegacy())
          .thenAnswer((_) async =>
              const Failure(ServerFailure(message: 'Unexpected error')));

      final result = await useCase();

      expect(result.isFailure, true);
      expect((result as Failure<void>).failure, isA<ServerFailure>());
    });

    test('calls repository exactly once', () async {
      when(() => mockRepository.migrateFromLegacy())
          .thenAnswer((_) async => const Success(null));

      await useCase();

      verify(() => mockRepository.migrateFromLegacy()).called(1);
      verifyNoMoreInteractions(mockRepository);
    });
  });
}
