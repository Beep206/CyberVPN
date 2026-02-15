import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';

/// Provides the shared [AppDatabase] instance for dependency injection.
///
/// The database is created lazily on first access via [AppDatabase.instance].
/// Disposing the provider closes the underlying SQLite connection.
///
/// Usage:
/// ```dart
/// final db = ref.watch(appDatabaseProvider);
/// final profiles = await db.select(db.profiles).get();
/// ```
final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase.instance;
  ref.onDispose(db.close);
  return db;
});
