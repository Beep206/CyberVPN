import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

part 'app_database.g.dart';

/// Type of a VPN profile — determines whether server configs come from
/// a remote subscription URL or were imported locally.
enum ProfileType { remote, local }

/// Stores VPN profiles.
///
/// Each profile is either a remote subscription (with a URL that can be
/// refreshed) or a local collection of manually-imported server configs.
class Profiles extends Table {
  /// Unique identifier (UUID v4).
  TextColumn get id => text()();

  /// Display name shown to the user.
  TextColumn get name => text().withLength(min: 1, max: 255)();

  /// Whether this is a remote subscription or local import group.
  TextColumn get type => textEnum<ProfileType>()();

  /// Subscription URL for remote profiles. Null for local profiles.
  ///
  /// Stored encrypted — see [EncryptedUrlStorage] for the encryption wrapper.
  TextColumn get subscriptionUrl => text().nullable()();

  /// Whether this profile is the currently active one for VPN connections.
  BoolColumn get isActive => boolean().withDefault(const Constant(false))();

  /// Sort position in the profile list (0-based).
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  /// When the profile was first created.
  DateTimeColumn get createdAt => dateTime()();

  /// When the profile was last updated (refreshed from subscription, etc.).
  DateTimeColumn get lastUpdatedAt => dateTime().nullable()();

  // ── Subscription metadata (remote profiles only) ──────────────────

  /// Total bytes uploaded through this subscription.
  IntColumn get uploadBytes => integer().withDefault(const Constant(0))();

  /// Total bytes downloaded through this subscription.
  IntColumn get downloadBytes => integer().withDefault(const Constant(0))();

  /// Total traffic allowance in bytes.
  IntColumn get totalBytes => integer().withDefault(const Constant(0))();

  /// When the subscription expires.
  DateTimeColumn get expiresAt => dateTime().nullable()();

  /// Auto-update interval in minutes (default 60 = 1 hour).
  IntColumn get updateIntervalMinutes =>
      integer().withDefault(const Constant(60))();

  /// Provider support URL.
  TextColumn get supportUrl => text().nullable()();

  /// Provider web page / test URL.
  TextColumn get testUrl => text().nullable()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

/// Stores individual VPN server configurations belonging to a profile.
///
/// Each row represents a single server entry (e.g. one VLESS node) that
/// was either parsed from a subscription body or imported individually.
class ProfileConfigs extends Table {
  /// Unique identifier (UUID v4).
  TextColumn get id => text()();

  /// The profile this config belongs to.
  TextColumn get profileId => text().references(Profiles, #id)();

  /// Display name (remark from the VPN URI or user-defined).
  TextColumn get name => text().withLength(min: 1, max: 255)();

  /// Server hostname or IP address.
  TextColumn get serverAddress => text()();

  /// Server port number.
  IntColumn get port => integer()();

  /// VPN protocol identifier (`vless`, `vmess`, `trojan`, `ss`).
  TextColumn get protocol => text()();

  /// Full configuration data as a JSON string.
  ///
  /// Contains transport settings, TLS config, UUID, password, and
  /// any protocol-specific parameters.
  TextColumn get configData => text()();

  /// Optional remark / label.
  TextColumn get remark => text().nullable()();

  /// Whether the user has marked this server as a favorite.
  BoolColumn get isFavorite => boolean().withDefault(const Constant(false))();

  /// Sort position within the parent profile.
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();

  /// Last measured latency in milliseconds. Null if not yet tested.
  IntColumn get latencyMs => integer().nullable()();

  /// When this config entry was created.
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column<Object>> get primaryKey => {id};
}

/// The application's local SQLite database powered by Drift.
///
/// Contains tables for VPN profiles and their server configurations.
/// Uses a lazy singleton pattern — the database file is created on first
/// access in the application documents directory.
///
/// Usage:
/// ```dart
/// final db = AppDatabase();
/// final profiles = await db.select(db.profiles).get();
/// ```
@DriftDatabase(tables: [Profiles, ProfileConfigs])
class AppDatabase extends _$AppDatabase {
  /// Creates the database with an optional [QueryExecutor].
  ///
  /// When no executor is provided, opens a native SQLite connection
  /// to `cybervpn.db` in the application documents directory.
  AppDatabase([QueryExecutor? executor])
      : super(executor ?? _openConnection());

  /// Lazy singleton instance.
  static AppDatabase? _instance;

  /// Returns the shared database instance.
  ///
  /// Creates the instance on first call. Subsequent calls return
  /// the same instance. Use [resetInstance] in tests to replace it.
  static AppDatabase get instance => _instance ??= AppDatabase();

  /// Replaces the singleton with a custom instance (for testing).
  static set instance(AppDatabase db) => _instance = db;

  /// Clears the singleton instance and closes the database connection.
  static Future<void> resetInstance() async {
    await _instance?.close();
    _instance = null;
  }

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) async {
          await m.createAll();
        },
        onUpgrade: (m, from, to) async {
          // Future migrations will go here.
          // Use `from` and `to` to run incremental migration steps.
        },
        beforeOpen: (details) async {
          // Enable foreign key enforcement.
          await customStatement('PRAGMA foreign_keys = ON');
        },
      );

  /// Opens a native SQLite connection to the application database file.
  static QueryExecutor _openConnection() {
    return LazyDatabase(() async {
      final dbFolder = await getApplicationDocumentsDirectory();
      final file = File(p.join(dbFolder.path, 'cybervpn.db'));
      return NativeDatabase.createInBackground(file);
    });
  }
}
