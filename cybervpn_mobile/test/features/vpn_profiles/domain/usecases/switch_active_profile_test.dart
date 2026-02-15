import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/switch_active_profile.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockVpnProfileRepository extends Mock implements ProfileRepository {}

void main() {
  late SwitchActiveProfileUseCase useCase;
  late MockVpnProfileRepository mockRepository;

  setUp(() {
    mockRepository = MockVpnProfileRepository();
    useCase = SwitchActiveProfileUseCase(mockRepository);
  });

  group('SwitchActiveProfileUseCase', () {
    test('returns Success when profile is set active', () async {
      when(() => mockRepository.setActive('p-1'))
          .thenAnswer((_) async => const Success(null));

      final result = await useCase('p-1');

      expect(result, isA<Success<void>>());
      verify(() => mockRepository.setActive('p-1')).called(1);
    });

    test('returns Failure when profile not found', () async {
      when(() => mockRepository.setActive('nonexistent'))
          .thenAnswer((_) async =>
              const Failure(CacheFailure(message: 'Profile not found')));

      final result = await useCase('nonexistent');

      expect(result.isFailure, true);
      final failure = (result as Failure<void>).failure;
      expect(failure, isA<CacheFailure>());
      expect(failure.message, 'Profile not found');
    });

    test('delegates to repository with exact profileId', () async {
      when(() => mockRepository.setActive(any()))
          .thenAnswer((_) async => const Success(null));

      await useCase('profile-abc-123');

      verify(() => mockRepository.setActive('profile-abc-123')).called(1);
    });
  });
}
