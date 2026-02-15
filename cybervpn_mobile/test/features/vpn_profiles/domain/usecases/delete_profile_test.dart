import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/delete_profile.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockVpnProfileRepository extends Mock implements ProfileRepository {}

void main() {
  late DeleteProfileUseCase useCase;
  late MockVpnProfileRepository mockRepository;

  setUp(() {
    mockRepository = MockVpnProfileRepository();
    useCase = DeleteProfileUseCase(mockRepository);
  });

  group('DeleteProfileUseCase', () {
    test('returns Success when profile is deleted', () async {
      when(() => mockRepository.delete('p-1'))
          .thenAnswer((_) async => const Success(null));

      final result = await useCase('p-1');

      expect(result, isA<Success<void>>());
      verify(() => mockRepository.delete('p-1')).called(1);
    });

    test('returns Failure when profile not found', () async {
      when(() => mockRepository.delete('nonexistent'))
          .thenAnswer((_) async =>
              const Failure(CacheFailure(message: 'Profile not found')));

      final result = await useCase('nonexistent');

      expect(result.isFailure, true);
      final failure = (result as Failure<void>).failure;
      expect(failure, isA<CacheFailure>());
    });

    test('returns Failure on database error', () async {
      when(() => mockRepository.delete(any()))
          .thenAnswer((_) async =>
              const Failure(CacheFailure(message: 'DB error')));

      final result = await useCase('p-1');

      expect(result.isFailure, true);
    });

    test('delegates to repository with exact profileId', () async {
      when(() => mockRepository.delete(any()))
          .thenAnswer((_) async => const Success(null));

      await useCase('profile-to-delete');

      verify(() => mockRepository.delete('profile-to-delete')).called(1);
    });
  });
}
