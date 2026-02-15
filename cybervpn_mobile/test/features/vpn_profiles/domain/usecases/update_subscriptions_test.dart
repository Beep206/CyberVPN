import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/update_subscriptions.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockVpnProfileRepository extends Mock implements ProfileRepository {}

void main() {
  late UpdateSubscriptionsUseCase useCase;
  late MockVpnProfileRepository mockRepository;

  setUp(() {
    mockRepository = MockVpnProfileRepository();
    useCase = UpdateSubscriptionsUseCase(mockRepository);
  });

  group('UpdateSubscriptionsUseCase', () {
    test('returns Success with count of updated profiles', () async {
      when(() => mockRepository.updateAllDueSubscriptions())
          .thenAnswer((_) async => const Success(3));

      final result = await useCase();

      expect(result, isA<Success<int>>());
      expect((result as Success<int>).data, 3);
      verify(() => mockRepository.updateAllDueSubscriptions()).called(1);
    });

    test('returns Success with 0 when no profiles due', () async {
      when(() => mockRepository.updateAllDueSubscriptions())
          .thenAnswer((_) async => const Success(0));

      final result = await useCase();

      expect(result.isSuccess, true);
      expect((result as Success<int>).data, 0);
    });

    test('returns Failure when update fails', () async {
      when(() => mockRepository.updateAllDueSubscriptions())
          .thenAnswer((_) async =>
              const Failure(NetworkFailure(message: 'Connection lost')));

      final result = await useCase();

      expect(result.isFailure, true);
      final failure = (result as Failure<int>).failure;
      expect(failure, isA<NetworkFailure>());
    });

    test('returns Failure on server error', () async {
      when(() => mockRepository.updateAllDueSubscriptions())
          .thenAnswer((_) async =>
              const Failure(ServerFailure(message: 'Server error', code: 503)));

      final result = await useCase();

      expect(result.isFailure, true);
      final failure = (result as Failure<int>).failure;
      expect(failure, isA<ServerFailure>());
      expect(failure.code, 503);
    });

    test('calls repository exactly once', () async {
      when(() => mockRepository.updateAllDueSubscriptions())
          .thenAnswer((_) async => const Success(1));

      await useCase();

      verify(() => mockRepository.updateAllDueSubscriptions()).called(1);
      verifyNoMoreInteractions(mockRepository);
    });
  });
}
