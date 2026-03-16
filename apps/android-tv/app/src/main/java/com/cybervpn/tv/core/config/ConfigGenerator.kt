package com.cybervpn.tv.core.config

import com.cybervpn.tv.core.model.ProxyNode
import com.cybervpn.tv.core.model.VpnProtocol
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonObjectBuilder
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

object ConfigGenerator {
    private const val DEFAULT_MULTIPLEX_MAX_CONNECTIONS = 5
    private const val DEFAULT_MULTIPLEX_MIN_STREAMS = 4

    /**
     * Converts a ProxyNode into a massive mapped Sing-box JSON configuration string.
     * Fully uses kotlinx.serialization.json builder to ensure structural integrity and no syntax errors.
     */
    fun generateSingboxConfig(node: ProxyNode): String {
        val root =
            buildJsonObject {
                put("log", buildLogConfig())
                put("dns", buildDnsConfig())
                put("inbounds", buildInbounds())
                put("outbounds", buildOutbounds(node))
                put("route", buildRouteConfig())
            }
        return root.toString()
    }

    private fun buildLogConfig(): JsonObject =
        buildJsonObject {
            put("level", "info")
            put("timestamp", true)
        }

    private fun buildDnsConfig(): JsonObject =
        buildJsonObject {
            put(
                "servers",
                buildJsonArray {
                    add(
                        buildJsonObject {
                            put("tag", "remote")
                            put("address", "https://8.8.8.8/dns-query")
                            put("detour", "proxy")
                        },
                    )
                    add(
                        buildJsonObject {
                            put("tag", "local")
                            put("address", "local")
                            put("detour", "direct")
                        },
                    )
                },
            )
            put(
                "rules",
                buildJsonArray {
                    add(
                        buildJsonObject {
                            put("outbound", buildJsonArray { add("any") })
                            put("server", "local")
                        },
                    )
                },
            )
        }

    private fun buildInbounds() =
        buildJsonArray {
            add(
                buildJsonObject {
                    put("type", "tun")
                    put("tag", "tun-in")
                    put("interface_name", "tun0")
                    put("inet4_address", "172.19.0.1/30")
                    put("auto_route", true)
                    put("strict_route", true)
                    put("stack", "system")
                    put("sniff", true)
                },
            )
        }

    private fun buildOutbounds(node: ProxyNode) =
        buildJsonArray {
            // Adding the primary proxy outbound based on protocol
            add(buildProxyOutbound(node))

            // Standard outbounds
            add(
                buildJsonObject {
                    put("type", "direct")
                    put("tag", "direct")
                },
            )
            add(
                buildJsonObject {
                    put("type", "block")
                    put("tag", "block")
                },
            )
            add(
                buildJsonObject {
                    put("type", "dns")
                    put("tag", "dns-out")
                },
            )
        }

    private fun buildProxyOutbound(node: ProxyNode): JsonObject =
        buildJsonObject {
            put("type", node.protocol.value)
            put("tag", "proxy")
            put("server", node.server)
            put("server_port", node.port)

            when (node.protocol) {
                VpnProtocol.VMESS -> buildVmessOutbound(node)
                VpnProtocol.VLESS -> buildVlessOutbound(node)
                VpnProtocol.TROJAN -> buildTrojanOutbound(node)
                VpnProtocol.SHADOWSOCKS -> buildShadowsocksOutbound(node)
                VpnProtocol.HYSTERIA2 -> buildHysteria2Outbound(node)
                VpnProtocol.UNKNOWN -> {}
            }

            buildTransportSettings(node)
        }

    private fun JsonObjectBuilder.buildVmessOutbound(node: ProxyNode) {
        node.uuid?.let { put("uuid", it) }
        put("security", node.method ?: "auto")
        put("alter_id", 0)
    }

    private fun JsonObjectBuilder.buildVlessOutbound(node: ProxyNode) {
        node.uuid?.let { put("uuid", it) }
        put("flow", "") // Optional flow tuning
    }

    private fun JsonObjectBuilder.buildTrojanOutbound(node: ProxyNode) {
        node.password?.let { put("password", it) }
    }

    private fun JsonObjectBuilder.buildShadowsocksOutbound(node: ProxyNode) {
        node.method?.let { put("method", it) }
        node.password?.let { put("password", it) }
    }

    private fun JsonObjectBuilder.buildHysteria2Outbound(node: ProxyNode) {
        node.password?.let { put("password", it) }
        node.obfs?.let {
            put(
                "obfs",
                buildJsonObject {
                    put("type", it)
                    node.obfsPassword?.let { pass -> put("password", pass) }
                },
            )
        }
        node.upMbps?.let { put("up_mbps", it) }
        node.downMbps?.let { put("down_mbps", it) }
    }

    private fun JsonObjectBuilder.buildTransportSettings(node: ProxyNode) {
        buildTlsSettings(node)
        buildMultiplexSettings()
        buildTransportPluginSettings(node)
    }

    private fun JsonObjectBuilder.buildTlsSettings(node: ProxyNode) {
        if (node.tls == "tls" || node.tls == "reality") {
            put(
                "tls",
                buildJsonObject {
                    put("enabled", true)
                    put("disable_sni", node.sni.isNullOrBlank())
                    node.sni?.let { put("server_name", it) }
                    node.alpn?.let { alpn ->
                        put(
                            "alpn",
                            buildJsonArray {
                                alpn.split(",").forEach { add(it.trim()) }
                            },
                        )
                    }

                    if (node.tls == "reality") {
                        put(
                            "reality",
                            buildJsonObject {
                                put("enabled", true)
                                node.pbk?.let { put("public_key", it) }
                                node.sid?.let { put("short_id", it) }
                            },
                        )
                    }
                },
            )
        }
    }

    private fun JsonObjectBuilder.buildMultiplexSettings() {
        put(
            "multiplex",
            buildJsonObject {
                put("enabled", true)
                put("protocol", "smux")
                put("max_connections", DEFAULT_MULTIPLEX_MAX_CONNECTIONS)
                put("min_streams", DEFAULT_MULTIPLEX_MIN_STREAMS)
                put("padding", true)
            },
        )
    }

    private fun JsonObjectBuilder.buildTransportPluginSettings(node: ProxyNode) {
        when (node.network) {
            "ws" -> {
                put(
                    "transport",
                    buildJsonObject {
                        put("type", "ws")
                        node.path?.let { put("path", it) }
                        node.host?.let { put("headers", buildJsonObject { put("Host", it) }) }
                    },
                )
            }
            "grpc" -> {
                put(
                    "transport",
                    buildJsonObject {
                        put("type", "grpc")
                        node.path?.let { put("service_name", it) }
                    },
                )
            }
        }
    }

    private fun buildRouteConfig(): JsonObject =
        buildJsonObject {
            put(
                "rules",
                buildJsonArray {
                    add(
                        buildJsonObject {
                            put("protocol", "dns")
                            put("outbound", "dns-out")
                        },
                    )
                    add(
                        buildJsonObject {
                            put("ip_is_private", true)
                            put("outbound", "direct")
                        },
                    )
                },
            )
            put("auto_detect_interface", true)
            put("final", "proxy")
        }
}
