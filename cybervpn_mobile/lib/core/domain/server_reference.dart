/// Lightweight server reference containing only ID and name.
///
/// Extracted to `core/domain/` to break the circular dependency between
/// the `vpn` and `servers` features. The VPN feature needs to reference
/// a server without importing the full `ServerEntity` from the servers
/// feature.
class ServerReference {
  const ServerReference({required this.id, required this.name});

  final String id;
  final String name;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ServerReference &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          name == other.name;

  @override
  int get hashCode => Object.hash(id, name);

  @override
  String toString() => 'ServerReference(id: $id, name: $name)';
}
