import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_app_bar.dart';

// ---------------------------------------------------------------------------
// LogViewerScreen
// ---------------------------------------------------------------------------

/// Full-screen log viewer with filtering, search, and export capabilities.
///
/// Features:
/// - Color-coded log levels (DEBUG, INFO, WARNING, ERROR)
/// - Filter chips for log level selection
/// - Keyword search field
/// - Auto-scroll to bottom toggle
/// - Entry count display
/// - Export logs as text file
/// - Clear logs with confirmation
class LogViewerScreen extends ConsumerStatefulWidget {
  const LogViewerScreen({super.key});

  @override
  ConsumerState<LogViewerScreen> createState() => _LogViewerScreenState();
}

class _LogViewerScreenState extends ConsumerState<LogViewerScreen> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();

  String _selectedLevel = 'ALL';
  String _searchKeyword = '';
  bool _autoScroll = true;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_autoScroll) {
        _scrollToBottom();
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _searchController.removeListener(_onSearchChanged);
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    setState(() {
      _searchKeyword = _searchController.text;
    });
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    }
  }

  List<LogEntry> _getFilteredLogs() {
    List<LogEntry> logs = AppLogger.entries;

    // Filter by level
    if (_selectedLevel != 'ALL') {
      logs = logs
          .where((entry) =>
              entry.level.toUpperCase() == _selectedLevel.toUpperCase())
          .toList();
    }

    // Filter by keyword (case-insensitive)
    if (_searchKeyword.isNotEmpty) {
      logs = logs
          .where((entry) =>
              entry.message.toLowerCase().contains(_searchKeyword.toLowerCase()))
          .toList();
    }

    return logs;
  }

  Color _getLogLevelColor(String level) {
    switch (level.toLowerCase()) {
      case 'debug':
        return Colors.grey;
      case 'info':
        return Colors.white;
      case 'warning':
        return Colors.orange;
      case 'error':
        return Colors.red;
      default:
        return Colors.white;
    }
  }

  Future<void> _exportLogs() async {
    final logs = AppLogger.exportLogs();
    if (logs.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No logs to export'),
            backgroundColor: CyberColors.darkBg,
          ),
        );
      }
      return;
    }

    unawaited(share_plus.Share.share(
      logs,
      subject: 'CyberVPN Logs - ${DateTime.now().toIso8601String()}',
    ));
  }

  Future<void> _clearLogs() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: CyberColors.darkBg,
        title: const Text(
          'Clear All Logs?',
          style: TextStyle(color: Colors.white),
        ),
        content: const Text(
          'This action cannot be undone',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      AppLogger.clearLogs();
      setState(() {});
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Logs cleared successfully'),
            backgroundColor: CyberColors.matrixGreen,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final filteredLogs = _getFilteredLogs();
    final totalCount = AppLogger.entryCount;

    return Scaffold(
      backgroundColor: CyberColors.deepNavy,
      appBar: CyberAppBar(
        title: 'Log Viewer',
        transparent: true,
        actions: [
          IconButton(
            icon: Icon(
              _autoScroll ? Icons.vertical_align_bottom : Icons.lock_open,
              color: _autoScroll ? CyberColors.neonCyan : Colors.white54,
            ),
            tooltip: 'Auto-scroll',
            onPressed: () {
              setState(() {
                _autoScroll = !_autoScroll;
                if (_autoScroll) {
                  _scrollToBottom();
                }
              });
            },
          ),
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Export Logs',
            onPressed: _exportLogs,
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Clear Logs',
            onPressed: _clearLogs,
          ),
        ],
      ),
      body: Column(
        children: [
          // Entry count display
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            color: Colors.white.withValues(alpha: 0.03),
            child: Row(
              children: [
                Icon(
                  Icons.article_outlined,
                  size: 16,
                  color: Colors.white.withValues(alpha: 0.5),
                ),
                const SizedBox(width: Spacing.xs),
                Text(
                  '$totalCount total entries',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.6),
                    fontSize: 12,
                    letterSpacing: 0.5,
                  ),
                ),
                if (filteredLogs.length != totalCount) ...[
                  const SizedBox(width: Spacing.sm),
                  Text(
                    '• ${filteredLogs.length} filtered',
                    style: TextStyle(
                      color: CyberColors.neonCyan.withValues(alpha: 0.8),
                      fontSize: 12,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ],
            ),
          ),

          // Search field
          Padding(
            padding: const EdgeInsets.all(Spacing.md),
            child: TextField(
              controller: _searchController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Search logs...',
                hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                prefixIcon: Icon(
                  Icons.search,
                  color: Colors.white.withValues(alpha: 0.5),
                ),
                suffixIcon: _searchKeyword.isNotEmpty
                    ? IconButton(
                        icon: Icon(
                          Icons.clear,
                          color: Colors.white.withValues(alpha: 0.5),
                        ),
                        onPressed: _searchController.clear,
                      )
                    : null,
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.sm),
                  borderSide: BorderSide(
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.sm),
                  borderSide: BorderSide(
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.sm),
                  borderSide: const BorderSide(
                    color: CyberColors.neonCyan,
                  ),
                ),
              ),
            ),
          ),

          // Filter chips
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              children: [
                _FilterChip(
                  label: 'ALL',
                  isSelected: _selectedLevel == 'ALL',
                  onSelected: () => setState(() => _selectedLevel = 'ALL'),
                ),
                const SizedBox(width: Spacing.sm),
                _FilterChip(
                  label: 'DEBUG',
                  isSelected: _selectedLevel == 'DEBUG',
                  color: Colors.grey,
                  onSelected: () => setState(() => _selectedLevel = 'DEBUG'),
                ),
                const SizedBox(width: Spacing.sm),
                _FilterChip(
                  label: 'INFO',
                  isSelected: _selectedLevel == 'INFO',
                  color: CyberColors.neonCyan,
                  onSelected: () => setState(() => _selectedLevel = 'INFO'),
                ),
                const SizedBox(width: Spacing.sm),
                _FilterChip(
                  label: 'WARNING',
                  isSelected: _selectedLevel == 'WARNING',
                  color: Colors.orange,
                  onSelected: () => setState(() => _selectedLevel = 'WARNING'),
                ),
                const SizedBox(width: Spacing.sm),
                _FilterChip(
                  label: 'ERROR',
                  isSelected: _selectedLevel == 'ERROR',
                  color: Colors.red,
                  onSelected: () => setState(() => _selectedLevel = 'ERROR'),
                ),
              ],
            ),
          ),

          const SizedBox(height: Spacing.sm),

          // Log entries list
          Expanded(
            child: filteredLogs.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.article_outlined,
                          color: Colors.white.withValues(alpha: 0.15),
                          size: 64,
                        ),
                        const SizedBox(height: Spacing.md),
                        Text(
                          totalCount == 0
                              ? 'No logs available'
                              : 'No logs match filters',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.3),
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    itemCount: filteredLogs.length,
                    itemBuilder: (context, index) {
                      final entry = filteredLogs[index];
                      return _LogEntryTile(
                        entry: entry,
                        color: _getLogLevelColor(entry.level),
                        searchKeyword: _searchKeyword,
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Filter Chip
// ---------------------------------------------------------------------------

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onSelected,
    this.color,
  });

  final String label;
  final bool isSelected;
  final VoidCallback onSelected;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final chipColor = color ?? CyberColors.neonCyan;

    return FilterChip(
      label: Text(
        label,
        style: TextStyle(
          color: isSelected ? CyberColors.deepNavy : chipColor,
          fontSize: 12,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ),
      selected: isSelected,
      onSelected: (_) => onSelected(),
      backgroundColor: Colors.white.withValues(alpha: 0.05),
      selectedColor: chipColor,
      checkmarkColor: CyberColors.deepNavy,
      side: BorderSide(
        color: isSelected ? chipColor : Colors.white.withValues(alpha: 0.1),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Log Entry Tile
// ---------------------------------------------------------------------------

class _LogEntryTile extends StatelessWidget {
  const _LogEntryTile({
    required this.entry,
    required this.color,
    this.searchKeyword = '',
  });

  final LogEntry entry;
  final Color color;
  final String searchKeyword;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.sm,
      ),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: Colors.white.withValues(alpha: 0.05),
          ),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timestamp
          SizedBox(
            width: 64,
            child: Text(
              _formatTime(entry.timestamp),
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.4),
                fontSize: 10,
                fontFamily: 'JetBrains Mono',
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),

          const SizedBox(width: Spacing.sm),

          // Level badge
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: 6,
              vertical: 2,
            ),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: color.withValues(alpha: 0.3),
              ),
            ),
            child: Text(
              entry.level.toUpperCase(),
              style: TextStyle(
                color: color,
                fontSize: 9,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
              ),
            ),
          ),

          const SizedBox(width: Spacing.sm),

          // Message
          Expanded(
            child: Text(
              entry.message,
              style: TextStyle(
                color: color.withValues(alpha: 0.9),
                fontSize: 12,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    final s = dt.second.toString().padLeft(2, '0');
    return '$h:$m:$s';
  }
}
