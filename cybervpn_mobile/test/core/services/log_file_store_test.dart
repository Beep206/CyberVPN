import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

void main() {
  late Directory tempDir;
  late LogFileStore store;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('cybervpn_logs_test');
    store = LogFileStore(
      supportDirectoryLoader: () async => tempDir,
      clock: () => DateTime.utc(2026, 4, 17, 12, 30, 45),
    );
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('records access and subscription logs into persistent files', () async {
    await store.record(
      LogEntry(
        timestamp: DateTime.utc(2026, 4, 17, 10),
        level: 'info',
        message: 'General message',
      ),
      category: 'vpn',
    );
    await store.record(
      LogEntry(
        timestamp: DateTime.utc(2026, 4, 17, 11),
        level: 'info',
        message: 'Subscription message',
      ),
      category: 'subscription',
    );

    final files = await store.listFiles();
    expect(
      files.map((file) => file.name),
      containsAll(<String>[
        LogFileStore.accessLogFileName,
        LogFileStore.subscriptionLogFileName,
      ]),
    );

    final accessContents = await store.readFile(files
        .firstWhere((file) => file.name == LogFileStore.accessLogFileName)
        .path);
    final subscriptionContents = await store.readFile(files
        .firstWhere(
          (file) => file.name == LogFileStore.subscriptionLogFileName,
        )
        .path);

    expect(accessContents, contains('General message'));
    expect(accessContents, contains('Subscription message'));
    expect(subscriptionContents, contains('Subscription message'));
    expect(subscriptionContents, isNot(contains('General message')));
  });

  test('writes redacted Xray runtime snapshots', () async {
    await store.writeXrayRuntimeSnapshot(
      '{"outbounds":[{"settings":{"vnext":[{"users":[{"id":"secret-uuid"}]}]}}]}',
      remark: 'Primary Server',
    );

    final files = await store.listFiles();
    final snapshot = files.firstWhere(
      (file) => file.kind == PersistentLogFileKind.xraySnapshot,
    );
    final contents = await store.readFile(snapshot.path);

    expect(snapshot.name, contains('Primary_Server'));
    expect(contents, contains('***REDACTED***'));
    expect(contents, isNot(contains('secret-uuid')));
  });

  test('clearPersistentLogs removes all tracked files', () async {
    await store.record(
      LogEntry(
        timestamp: DateTime.utc(2026, 4, 17, 10),
        level: 'info',
        message: 'General message',
      ),
      category: 'vpn',
    );
    await store.writeXrayRuntimeSnapshot('{"log":{}}');

    expect(await store.listFiles(), isNotEmpty);

    await store.clearPersistentLogs();

    expect(await store.listFiles(), isEmpty);
  });
}
