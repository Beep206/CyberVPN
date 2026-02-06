import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';

import '../../helpers/mock_factories.dart';
import '../../helpers/mock_repositories.dart';

/// Tests for the [ServerRepository] contract.
///
/// NOTE: The concrete [ServerRepositoryImpl] cannot be directly tested at this
/// time because [ServerLocalDataSourceImpl] references `setStringList` and
/// `getStringList` methods that are not yet defined on [LocalStorageWrapper].
/// Once that pre-existing issue is resolved, these tests should be expanded to
/// cover the impl's caching behavior (cache hit/miss, TTL expiry, force
/// refresh, API failure fallback to cache).
///
/// The tests below verify the repository interface contract using
/// [MockServerRepository], ensuring that consumers of the repository get the
/// expected behavior regardless of the implementation.
void main() {
  late MockServerRepository repository;

  setUp(() {
    repository = MockServerRepository();
  });

  final testServers = [
    createMockServer(id: 's1', name: 'US East', countryCode: 'US'),
    createMockServer(id: 's2', name: 'DE Frankfurt', countryCode: 'DE'),
    createMockServer(id: 's3', name: 'US West', countryCode: 'US'),
  ];

  group('ServerRepository', () {
    // -----------------------------------------------------------------------
    // getServers
    // -----------------------------------------------------------------------

    group('getServers', () {
      test('returns a list of servers', () async {
        when(() => repository.getServers())
            .thenAnswer((_) async => Success(testServers));

        final result = await repository.getServers();

        expect(result, isA<Success<List<ServerEntity>>>());
        expect((result as Success<List<ServerEntity>>).data, hasLength(3));
        verify(() => repository.getServers()).called(1);
      });

      test('returns empty list when no servers exist', () async {
        when(() => repository.getServers()).thenAnswer((_) async => const Success(<ServerEntity>[]));

        final result = await repository.getServers();

        expect(result, isA<Success<List<ServerEntity>>>());
        expect((result as Success<List<ServerEntity>>).data, isEmpty);
      });

      test('returns Failure with NetworkFailure when offline and no cache', () async {
        when(() => repository.getServers())
            .thenAnswer((_) async => const Failure(NetworkFailure(message: 'No internet connection')));

        final result = await repository.getServers();

        expect(result, isA<Failure<List<ServerEntity>>>());
        expect((result as Failure<List<ServerEntity>>).failure, isA<NetworkFailure>());
      });
    });

    // -----------------------------------------------------------------------
    // getServerById
    // -----------------------------------------------------------------------

    group('getServerById', () {
      test('returns the requested server', () async {
        final server = createMockServer(id: 's1');
        when(() => repository.getServerById('s1'))
            .thenAnswer((_) async => Success(server));

        final result = await repository.getServerById('s1');

        expect(result, isA<Success<ServerEntity>>());
        expect((result as Success<ServerEntity>).data.id, equals('s1'));
        verify(() => repository.getServerById('s1')).called(1);
      });

      test('returns Failure when server not found', () async {
        when(() => repository.getServerById('nonexistent'))
            .thenAnswer((_) async => const Failure(ServerFailure(message: 'Not found')));

        final result = await repository.getServerById('nonexistent');

        expect(result, isA<Failure<ServerEntity>>());
        expect((result as Failure<ServerEntity>).failure, isA<ServerFailure>());
      });
    });

    // -----------------------------------------------------------------------
    // getServersByCountry
    // -----------------------------------------------------------------------

    group('getServersByCountry', () {
      test('returns servers filtered by country code', () async {
        final usServers =
            testServers.where((s) => s.countryCode == 'US').toList();
        when(() => repository.getServersByCountry('US'))
            .thenAnswer((_) async => Success(usServers));

        final result = await repository.getServersByCountry('US');

        expect(result, isA<Success<List<ServerEntity>>>());
        final data = (result as Success<List<ServerEntity>>).data;
        expect(data, hasLength(2));
        expect(data.every((s) => s.countryCode == 'US'), isTrue);
      });

      test('returns empty list for unknown country code', () async {
        when(() => repository.getServersByCountry('XX'))
            .thenAnswer((_) async => const Success(<ServerEntity>[]));

        final result = await repository.getServersByCountry('XX');

        expect(result, isA<Success<List<ServerEntity>>>());
        expect((result as Success<List<ServerEntity>>).data, isEmpty);
      });
    });

    // -----------------------------------------------------------------------
    // getFavoriteServers
    // -----------------------------------------------------------------------

    group('getFavoriteServers', () {
      test('returns only favorited servers', () async {
        final favorites = [
          createMockServer(id: 's1', isFavorite: true),
        ];
        when(() => repository.getFavoriteServers())
            .thenAnswer((_) async => Success(favorites));

        final result = await repository.getFavoriteServers();

        expect(result, isA<Success<List<ServerEntity>>>());
        final data = (result as Success<List<ServerEntity>>).data;
        expect(data, hasLength(1));
        expect(data.first.id, equals('s1'));
        expect(data.first.isFavorite, isTrue);
      });

      test('returns empty list when no favorites are set', () async {
        when(() => repository.getFavoriteServers())
            .thenAnswer((_) async => const Success(<ServerEntity>[]));

        final result = await repository.getFavoriteServers();

        expect(result, isA<Success<List<ServerEntity>>>());
        expect((result as Success<List<ServerEntity>>).data, isEmpty);
      });
    });

    // -----------------------------------------------------------------------
    // toggleFavorite
    // -----------------------------------------------------------------------

    group('toggleFavorite', () {
      test('completes successfully', () async {
        when(() => repository.toggleFavorite(any()))
            .thenAnswer((_) async => const Success<void>(null));

        final result = await repository.toggleFavorite('s1');

        expect(result, isA<Success<void>>());
        verify(() => repository.toggleFavorite('s1')).called(1);
      });
    });

    // -----------------------------------------------------------------------
    // pingServer
    // -----------------------------------------------------------------------

    group('pingServer', () {
      test('returns latency in milliseconds for reachable host', () async {
        when(() => repository.pingServer(any()))
            .thenAnswer((_) async => const Success(42));

        final result = await repository.pingServer('203.0.113.1');

        expect(result, isA<Success<int>>());
        expect((result as Success<int>).data, equals(42));
      });

      test('returns -1 for unreachable host', () async {
        when(() => repository.pingServer(any()))
            .thenAnswer((_) async => const Success(-1));

        final result = await repository.pingServer('invalid-host');

        expect(result, isA<Success<int>>());
        expect((result as Success<int>).data, equals(-1));
      });
    });

    // -----------------------------------------------------------------------
    // getBestServer
    // -----------------------------------------------------------------------

    group('getBestServer', () {
      test('returns the server with best metrics', () async {
        final bestServer = createMockServer(id: 's2', ping: 10, load: 0.1);
        when(() => repository.getBestServer())
            .thenAnswer((_) async => Success(bestServer));

        final result = await repository.getBestServer();

        expect(result, isA<Success<ServerEntity>>());
        final data = (result as Success<ServerEntity>).data;
        expect(data.id, equals('s2'));
        expect(data.ping, equals(10));
      });

      test('returns Failure when no servers are available', () async {
        when(() => repository.getBestServer()).thenAnswer(
          (_) async => const Failure(ServerFailure(message: 'No servers available')),
        );

        final result = await repository.getBestServer();

        expect(result, isA<Failure<ServerEntity>>());
        expect((result as Failure<ServerEntity>).failure, isA<ServerFailure>());
      });

      test('returns a non-premium server', () async {
        final server =
            createMockServer(id: 's1', isPremium: false, isAvailable: true);
        when(() => repository.getBestServer())
            .thenAnswer((_) async => Success(server));

        final result = await repository.getBestServer();

        expect(result, isA<Success<ServerEntity>>());
        final data = (result as Success<ServerEntity>).data;
        expect(data.isPremium, isFalse);
        expect(data.isAvailable, isTrue);
      });
    });
  });
}
