import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/features/servers/data/datasources/favorites_local_datasource.dart';

void main() {
  late FavoritesLocalDatasource datasource;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    datasource = FavoritesLocalDatasource(prefs);
  });

  group('FavoritesLocalDatasource', () {
    // -----------------------------------------------------------------------
    // getFavoriteIds
    // -----------------------------------------------------------------------

    group('getFavoriteIds', () {
      test('returns empty list when no favorites are stored', () async {
        final result = await datasource.getFavoriteIds();

        expect(result, isEmpty);
      });

      test('returns stored favorites in correct order', () async {
        await datasource.saveFavoriteIds(['s1', 's2', 's3']);

        final result = await datasource.getFavoriteIds();

        expect(result, equals(['s1', 's2', 's3']));
      });
    });

    // -----------------------------------------------------------------------
    // addFavorite
    // -----------------------------------------------------------------------

    group('addFavorite', () {
      test('adds a server to favorites and persists it', () async {
        final added = await datasource.addFavorite('s1');

        expect(added, isTrue);
        final ids = await datasource.getFavoriteIds();
        expect(ids, contains('s1'));
      });

      test('returns false when adding a duplicate', () async {
        await datasource.addFavorite('s1');

        final addedAgain = await datasource.addFavorite('s1');

        expect(addedAgain, isFalse);
        final ids = await datasource.getFavoriteIds();
        expect(ids, hasLength(1));
      });

      test('returns false when max favorites limit is reached', () async {
        // Fill to max (10)
        for (int i = 0; i < FavoritesLocalDatasource.maxFavorites; i++) {
          await datasource.addFavorite('s$i');
        }

        final added = await datasource.addFavorite('overflow');

        expect(added, isFalse);
        final ids = await datasource.getFavoriteIds();
        expect(ids, hasLength(FavoritesLocalDatasource.maxFavorites));
        expect(ids, isNot(contains('overflow')));
      });

      test('preserves existing order when adding', () async {
        await datasource.addFavorite('s1');
        await datasource.addFavorite('s2');
        await datasource.addFavorite('s3');

        final ids = await datasource.getFavoriteIds();

        expect(ids, equals(['s1', 's2', 's3']));
      });
    });

    // -----------------------------------------------------------------------
    // removeFavorite
    // -----------------------------------------------------------------------

    group('removeFavorite', () {
      test('removes a server from favorites', () async {
        await datasource.addFavorite('s1');
        await datasource.addFavorite('s2');

        final removed = await datasource.removeFavorite('s1');

        expect(removed, isTrue);
        final ids = await datasource.getFavoriteIds();
        expect(ids, equals(['s2']));
      });

      test('returns false when removing a non-existent favorite', () async {
        final removed = await datasource.removeFavorite('nonexistent');

        expect(removed, isFalse);
      });

      test('persists removal', () async {
        await datasource.addFavorite('s1');
        await datasource.removeFavorite('s1');

        final ids = await datasource.getFavoriteIds();

        expect(ids, isEmpty);
      });
    });

    // -----------------------------------------------------------------------
    // reorderFavorites
    // -----------------------------------------------------------------------

    group('reorderFavorites', () {
      test('moves item down in the list', () async {
        await datasource.saveFavoriteIds(['s1', 's2', 's3']);

        // Move s1 (index 0) to after s2 (newIndex 2, adjusts to 1)
        await datasource.reorderFavorites(0, 2);

        final ids = await datasource.getFavoriteIds();
        expect(ids, equals(['s2', 's1', 's3']));
      });

      test('moves item up in the list', () async {
        await datasource.saveFavoriteIds(['s1', 's2', 's3']);

        // Move s3 (index 2) to position 0
        await datasource.reorderFavorites(2, 0);

        final ids = await datasource.getFavoriteIds();
        expect(ids, equals(['s3', 's1', 's2']));
      });

      test('does nothing for out-of-bounds indices', () async {
        await datasource.saveFavoriteIds(['s1', 's2']);

        await datasource.reorderFavorites(-1, 0);
        final ids1 = await datasource.getFavoriteIds();
        expect(ids1, equals(['s1', 's2']));

        await datasource.reorderFavorites(0, 5);
        final ids2 = await datasource.getFavoriteIds();
        expect(ids2, equals(['s1', 's2']));
      });

      test('moving same index to same position is a no-op', () async {
        await datasource.saveFavoriteIds(['s1', 's2', 's3']);

        await datasource.reorderFavorites(1, 1);

        final ids = await datasource.getFavoriteIds();
        expect(ids, equals(['s1', 's2', 's3']));
      });

      test('persists reorder', () async {
        await datasource.saveFavoriteIds(['s1', 's2', 's3']);
        await datasource.reorderFavorites(0, 2);

        // Re-read from storage to confirm persistence
        final ids = await datasource.getFavoriteIds();
        expect(ids, equals(['s2', 's1', 's3']));
      });
    });

    // -----------------------------------------------------------------------
    // saveFavoriteIds
    // -----------------------------------------------------------------------

    group('saveFavoriteIds', () {
      test('overwrites previous favorites', () async {
        await datasource.saveFavoriteIds(['s1', 's2']);
        await datasource.saveFavoriteIds(['s3']);

        final ids = await datasource.getFavoriteIds();

        expect(ids, equals(['s3']));
      });

      test('handles empty list', () async {
        await datasource.saveFavoriteIds(['s1']);
        await datasource.saveFavoriteIds([]);

        final ids = await datasource.getFavoriteIds();

        expect(ids, isEmpty);
      });
    });
  });
}
