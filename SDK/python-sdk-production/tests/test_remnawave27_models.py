from remnawave.models import (
    GetMetadataResponseDto,
    GetNodePluginsResponseDto,
    GetNodesMetricsResponseDto,
    GetRecapResponseDto,
    GetRemnawaveHealthResponseDto,
    GetUserMetadataResponseDto,
)


def test_health_runtime_metrics_payload_parses() -> None:
    payload = {
        "runtimeMetrics": [
            {
                "rss": 104857600,
                "heapUsed": 73400320,
                "heapTotal": 94371840,
                "external": 4096,
                "arrayBuffers": 2048,
                "eventLoopDelayMs": 2.4,
                "eventLoopP99Ms": 5.9,
                "activeHandles": 31,
                "uptime": 86400.0,
                "pid": 123,
                "timestamp": 1710000000,
                "instanceId": "0",
                "instanceType": "api",
            }
        ]
    }

    dto = GetRemnawaveHealthResponseDto.model_validate(payload)
    assert dto.runtime_metrics[0].heap_used == 73400320
    assert dto.runtime_metrics[0].instance_type == "api"


def test_nodes_metrics_payload_parses() -> None:
    payload = {
        "nodes": [
            {
                "nodeUuid": "5d33e3fd-f9f6-4bf7-9f03-0b7af3a40db2",
                "nodeName": "ams-edge-01",
                "countryEmoji": "🇳🇱",
                "providerName": "hetzner",
                "usersOnline": 12,
                "inboundsStats": [{"tag": "vless-xhttp", "upload": "1024", "download": "2048"}],
                "outboundsStats": [{"tag": "direct", "upload": "512", "download": "256"}],
            }
        ]
    }

    dto = GetNodesMetricsResponseDto.model_validate(payload)
    assert dto.nodes[0].node_name == "ams-edge-01"
    assert dto.nodes[0].inbounds_stats[0].tag == "vless-xhttp"


def test_metadata_and_recap_payloads_parse() -> None:
    metadata = GetMetadataResponseDto.model_validate(
        {
            "version": "2.7.4",
            "build": {"time": "2026-04-08T00:00:00Z", "number": "42"},
            "git": {
                "backend": {
                    "commitSha": "abc123",
                    "branch": "main",
                    "commitUrl": "https://github.com/remnawave/backend/commit/abc123",
                },
                "frontend": {
                    "commitSha": "def456",
                    "commitUrl": "https://github.com/remnawave/panel/commit/def456",
                },
            },
        }
    )
    recap = GetRecapResponseDto.model_validate(
        {
            "thisMonth": {"users": 12, "traffic": "1048576"},
            "total": {
                "users": 100,
                "nodes": 7,
                "traffic": "987654321",
                "nodesRam": "68719476736",
                "nodesCpuCores": 24,
                "distinctCountries": 4,
            },
            "version": "2.7.4",
            "initDate": "2026-04-01T00:00:00+00:00",
        }
    )
    assert metadata.git.backend.branch == "main"
    assert recap.total.nodes == 7


def test_node_plugins_and_metadata_payloads_parse() -> None:
    plugins = GetNodePluginsResponseDto.model_validate(
        {
            "total": 1,
            "nodePlugins": [
                {
                    "uuid": "c6a88353-bd47-482d-8b66-c08e640cf8bf",
                    "viewPosition": 1,
                    "name": "torrent-blocker-main",
                    "pluginConfig": {
                        "sharedLists": [{"name": "ext:allowlist", "type": "ipList", "items": ["1.1.1.1"]}],
                        "torrentBlocker": {
                            "enabled": True,
                            "blockDuration": 3600,
                            "ignoreLists": {"ip": ["ext:allowlist"], "userId": [1]},
                        },
                    },
                }
            ],
        }
    )
    metadata = GetUserMetadataResponseDto.model_validate({"metadata": {"source": "telegram", "plan": "trial"}})
    assert plugins.node_plugins[0].name == "torrent-blocker-main"
    assert metadata.metadata["source"] == "telegram"
