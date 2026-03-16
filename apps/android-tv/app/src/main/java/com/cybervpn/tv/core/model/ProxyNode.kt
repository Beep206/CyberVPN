package com.cybervpn.tv.core.model

import kotlinx.serialization.Serializable

@Serializable
enum class VpnProtocol(val value: String) {
    VMESS("vmess"),
    VLESS("vless"),
    TROJAN("trojan"),
    SHADOWSOCKS("shadowsocks"),
    HYSTERIA2("hysteria2"),
    UNKNOWN("unknown"),
}

@Serializable
data class ProxyNode(
    val id: String = "",
    val name: String = "",
    val protocol: VpnProtocol = VpnProtocol.UNKNOWN,
    val server: String = "",
    val port: Int = 0,
    // Auth & Identification
    val uuid: String? = null,
    val password: String? = null,
    // Used by SS
    val method: String? = null,
    // Transport & TLS
    // "tls" or "reality"
    val tls: String? = null,
    val sni: String? = null,
    // e.g. "chrome"
    val fingerprint: String? = null,
    // e.g. "h2,http/1.1"
    val alpn: String? = null,
    // Reality specific
    // public key
    val pbk: String? = null,
    // short id
    val sid: String? = null,
    // Obfuscation / Transport Types
    // "tcp", "ws", "grpc"
    val network: String? = null,
    // ws path, or grpc serviceName
    val path: String? = null,
    // ws host
    val host: String? = null,
    // Hysteria2 specific
    val upMbps: Int? = null,
    val downMbps: Int? = null,
    // "salamander"
    val obfs: String? = null,
    val obfsPassword: String? = null,
)
