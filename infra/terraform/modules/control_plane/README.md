# control_plane module

Creates a single Hetzner host intended for CyberVPN control-plane workloads.

This wrapper keeps the server lifecycle identical to `edge_node`, but adds a
stable place for control-plane specific labels such as `workload_roles`.
