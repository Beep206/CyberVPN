import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/add_remote_profile.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockVpnProfileRepository extends Mock implements ProfileRepository {}

void main() {
  late AddRemoteProfileUseCase useCase;
  late MockVpnProfileRepository mockRepository;

  final now = DateTime(2026, 2, 15);
  const testUrl = 'https://sub.example.com/token';

  setUp(() {
    mockRepository = MockVpnProfileRepository();
    useCase = AddRemoteProfileUseCase(mockRepository);
  });

  group('AddRemoteProfileUseCase', () {
    test('returns Success with VpnProfile on success', () async {
      final profile = VpnProfile.remote(
        id: 'p-1',
        name: 'My Sub',
        subscriptionUrl: testUrl,
        sortOrder: 0,
        createdAt: now,
      );
      when(() => mockRepository.addRemoteProfile(testUrl, name: null))
          .thenAnswer((_) async => Success(profile));

      final result = await useCase(testUrl);

      expect(result, isA<Success<VpnProfile>>());
      expect((result as Success<VpnProfile>).data, profile);
      verify(() => mockRepository.addRemoteProfile(testUrl, name: null))
          .called(1);
    });

    test('passes optional name to repository', () async {
      final profile = VpnProfile.remote(
        id: 'p-2',
        name: 'Custom Name',
        subscriptionUrl: testUrl,
        sortOrder: 0,
        createdAt: now,
      );
      when(() => mockRepository.addRemoteProfile(testUrl, name: 'Custom Name'))
          .thenAnswer((_) async => Success(profile));

      final result = await useCase(testUrl, name: 'Custom Name');

      expect(result.isSuccess, true);
      verify(() =>
              mockRepository.addRemoteProfile(testUrl, name: 'Custom Name'))
          .called(1);
    });

    test('returns Failure when repository fails', () async {
      when(() => mockRepository.addRemoteProfile(testUrl, name: null))
          .thenAnswer((_) async =>
              const Failure(ServerFailure(message: 'Fetch failed', code: 500)));

      final result = await useCase(testUrl);

      expect(result, isA<Failure<VpnProfile>>());
      expect(result.isFailure, true);
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.addRemoteProfile(testUrl, name: null))
          .thenAnswer((_) async => const Failure(
              NetworkFailure(message: 'No internet connection')));

      final result = await useCase(testUrl);

      expect(result.isFailure, true);
      final failure = (result as Failure<VpnProfile>).failure;
      expect(failure, isA<NetworkFailure>());
    });
  });
}
