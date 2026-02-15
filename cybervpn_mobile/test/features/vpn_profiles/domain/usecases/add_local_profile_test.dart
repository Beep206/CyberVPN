import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/usecases/add_local_profile.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockVpnProfileRepository extends Mock implements ProfileRepository {}

void main() {
  late AddLocalProfileUseCase useCase;
  late MockVpnProfileRepository mockRepository;

  final now = DateTime(2026, 2, 15);

  final testServers = [
    ProfileServer(
      id: 'srv-1',
      profileId: 'p-1',
      name: 'US East',
      serverAddress: '203.0.113.1',
      port: 443,
      protocol: VpnProtocol.vless,
      configData: '{"uuid":"test"}',
      sortOrder: 0,
      createdAt: now,
    ),
  ];

  setUpAll(() {
    registerFallbackValue(<ProfileServer>[]);
  });

  setUp(() {
    mockRepository = MockVpnProfileRepository();
    useCase = AddLocalProfileUseCase(mockRepository);
  });

  group('AddLocalProfileUseCase', () {
    test('returns Success with local VpnProfile', () async {
      final profile = VpnProfile.local(
        id: 'p-1',
        name: 'Local Configs',
        sortOrder: 0,
        createdAt: now,
        servers: testServers,
      );
      when(() => mockRepository.addLocalProfile('Local Configs', testServers))
          .thenAnswer((_) async => Success(profile));

      final result = await useCase('Local Configs', testServers);

      expect(result, isA<Success<VpnProfile>>());
      expect((result as Success<VpnProfile>).data.id, 'p-1');
      verify(() => mockRepository.addLocalProfile('Local Configs', testServers))
          .called(1);
    });

    test('passes empty server list to repository', () async {
      final profile = VpnProfile.local(
        id: 'p-2',
        name: 'Empty',
        sortOrder: 0,
        createdAt: now,
      );
      when(() => mockRepository.addLocalProfile('Empty', const []))
          .thenAnswer((_) async => Success(profile));

      final result = await useCase('Empty', const []);

      expect(result.isSuccess, true);
      verify(() => mockRepository.addLocalProfile('Empty', const [])).called(1);
    });

    test('returns Failure when repository fails', () async {
      when(() => mockRepository.addLocalProfile(
              any(), any(that: isA<List<ProfileServer>>())))
          .thenAnswer((_) async =>
              const Failure(CacheFailure(message: 'DB write failed')));

      final result = await useCase('Test', testServers);

      expect(result.isFailure, true);
      final failure = (result as Failure<VpnProfile>).failure;
      expect(failure, isA<CacheFailure>());
    });
  });
}
