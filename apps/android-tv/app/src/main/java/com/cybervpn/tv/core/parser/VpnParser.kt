package com.cybervpn.tv.core.parser

import android.net.Uri
import android.util.Base64
import com.cybervpn.tv.core.model.ProxyNode
import com.cybervpn.tv.core.model.VpnProtocol
import java.net.URLDecoder
import java.util.UUID

@Suppress("ReturnCount")
object VpnParser {
    /**
     * Parses any supported VPN share link into a ProxyNode model.
     * Guaranteed not to throw exceptions on malformed input (returns null instead).
     */
    fun parse(link: String): ProxyNode? =
        runCatching {
            val trimmed = link.trim()
            val uri = Uri.parse(trimmed) ?: return@runCatching null

            when (uri.scheme?.lowercase()) {
                "vless" -> parseVless(uri)
                "trojan" -> parseTrojan(uri)
                "ss" -> parseShadowsocks(uri, trimmed)
                "hysteria2", "hy2" -> parseHysteria2(uri)
                "vmess" -> parseVmess(trimmed)
                else -> null
            }
        }.getOrNull()

    private fun parseVless(uri: Uri): ProxyNode? {
        val server = uri.host ?: return null
        val port = uri.port.takeIf { it > 0 } ?: return null
        val uuid = uri.userInfo ?: return null
        val name = uri.fragment?.let { URLDecoder.decode(it, "UTF-8") } ?: "VLESS Node"

        return ProxyNode(
            id = UUID.randomUUID().toString(),
            name = name,
            protocol = VpnProtocol.VLESS,
            server = server,
            port = port,
            uuid = uuid,
            tls = uri.getQueryParameter("security"),
            sni = uri.getQueryParameter("sni"),
            fingerprint = uri.getQueryParameter("fp"),
            alpn = uri.getQueryParameter("alpn"),
            pbk = uri.getQueryParameter("pbk"),
            sid = uri.getQueryParameter("sid"),
            network = uri.getQueryParameter("type"),
            path = uri.getQueryParameter("path"),
            host = uri.getQueryParameter("host"),
        )
    }

    private fun parseTrojan(uri: Uri): ProxyNode? {
        val server = uri.host ?: return null
        val port = uri.port.takeIf { it > 0 } ?: return null
        val password = uri.userInfo ?: return null
        val name = uri.fragment?.let { URLDecoder.decode(it, "UTF-8") } ?: "Trojan Node"

        return ProxyNode(
            id = UUID.randomUUID().toString(),
            name = name,
            protocol = VpnProtocol.TROJAN,
            server = server,
            port = port,
            password = password,
            tls = uri.getQueryParameter("security") ?: "tls",
            sni = uri.getQueryParameter("sni"),
            fingerprint = uri.getQueryParameter("fp"),
            alpn = uri.getQueryParameter("alpn"),
            network = uri.getQueryParameter("type"),
            path = uri.getQueryParameter("path"),
            host = uri.getQueryParameter("host"),
        )
    }

    private fun parseHysteria2(uri: Uri): ProxyNode? {
        val server = uri.host ?: return null
        val port = uri.port.takeIf { it > 0 } ?: return null
        val password = uri.userInfo ?: return null
        val name = uri.fragment?.let { URLDecoder.decode(it, "UTF-8") } ?: "Hysteria2 Node"

        return ProxyNode(
            id = UUID.randomUUID().toString(),
            name = name,
            protocol = VpnProtocol.HYSTERIA2,
            server = server,
            port = port,
            password = password,
            sni = uri.getQueryParameter("sni"),
            obfs = uri.getQueryParameter("obfs"),
            obfsPassword = uri.getQueryParameter("obfs-password"),
            upMbps = uri.getQueryParameter("upmbps")?.toIntOrNull(),
            downMbps = uri.getQueryParameter("downmbps")?.toIntOrNull(),
        )
    }

    private fun parseShadowsocks(
        uri: Uri,
        rawLink: String,
    ): ProxyNode? {
        val name = uri.fragment?.let { URLDecoder.decode(it, "UTF-8") } ?: "Shadowsocks Node"

        // Handles standard SIP002 (e.g. ss://method:password@host:port)
        if (uri.userInfo != null && uri.host != null && uri.port > 0) {
            val userInfoStr = uri.userInfo ?: return null
            val decodedUserInfo = decodeBase64Safe(userInfoStr) ?: userInfoStr
            val parts = decodedUserInfo.split(":")
            if (parts.size >= 2) {
                return ProxyNode(
                    id = UUID.randomUUID().toString(),
                    name = name,
                    protocol = VpnProtocol.SHADOWSOCKS,
                    server = uri.host ?: return null,
                    port = uri.port,
                    method = parts[0],
                    password = parts.drop(1).joinToString(":"),
                )
            }
        }

        // Handles purely Base64 encoded payload (e.g. ss://BASE64STRING#name)
        val payloadLink = rawLink.replaceFirst("ss://", "").substringBefore("#")
        val decodedPayload = decodeBase64Safe(payloadLink) ?: return null

        // decoded format: method:password@host:port
        val splitAt = decodedPayload.lastIndexOf("@")
        if (splitAt == -1) return null

        val userInfo = decodedPayload.substring(0, splitAt)
        val hostPort = decodedPayload.substring(splitAt + 1)

        val userParts = userInfo.split(":")
        val hpParts = hostPort.split(":")

        if (userParts.size < 2 || hpParts.size < 2) return null

        return ProxyNode(
            id = UUID.randomUUID().toString(),
            name = name,
            protocol = VpnProtocol.SHADOWSOCKS,
            server = hpParts[0],
            port = hpParts[1].toIntOrNull() ?: return null,
            method = userParts[0],
            password = userParts.drop(1).joinToString(":"),
        )
    }

    private fun parseVmess(rawLink: String): ProxyNode? {
        val b64Payload = rawLink.replaceFirst("vmess://", "")
        val jsonPayload = decodeBase64Safe(b64Payload) ?: return null

        // We use org.json dynamically or simple extraction since it's just a payload map
        // but since we shouldn't fail, we'll try to extract fields manually or rely on kotlinx.serialization internally if registered.
        // For simplicity and to avoid importing new libs like org.json.JSONObject (which throws), we'll parse it simply or using Kotlinx JSON.

        return runCatching {
            val jsonElement = kotlinx.serialization.json.Json.parseToJsonElement(jsonPayload)
            val obj = jsonElement.kotlinx.serialization.json.jsonObject

            val ps = obj["ps"]?.kotlinx.serialization.json.jsonPrimitive?.content ?: "VMess Node"
            val add = obj["add"]?.kotlinx.serialization.json.jsonPrimitive?.content ?: return@runCatching null
            val port = obj["port"]?.kotlinx.serialization.json.jsonPrimitive?.content?.toIntOrNull() ?: return@runCatching null
            val id = obj["id"]?.kotlinx.serialization.json.jsonPrimitive?.content ?: return@runCatching null
            val net = obj["net"]?.kotlinx.serialization.json.jsonPrimitive?.content
            val type = obj["type"]?.kotlinx.serialization.json.jsonPrimitive?.content
            val tls = obj["tls"]?.kotlinx.serialization.json.jsonPrimitive?.content
            val sni = obj["sni"]?.kotlinx.serialization.json.jsonPrimitive?.content
            val path = obj["path"]?.kotlinx.serialization.json.jsonPrimitive?.content
            val host = obj["host"]?.kotlinx.serialization.json.jsonPrimitive?.content

            ProxyNode(
                id = UUID.randomUUID().toString(),
                name = ps,
                protocol = VpnProtocol.VMESS,
                server = add,
                port = port,
                uuid = id,
                network = net,
                tls = tls,
                sni = sni,
                path = path,
                host = host,
                method = type,
            )
        }.getOrNull()
    }

    private fun decodeBase64Safe(input: String): String? {
        return runCatching {
            // Android Base64
            // Remove lingering newlines if any
            val cleanStr = input.trim().replace("\n", "").replace("\r", "")
            // Handle padding variations safely
            val decodedBytes = Base64.decode(cleanStr, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
            String(decodedBytes, Charsets.UTF_8)
        }.recoverCatching {
            // Fallback decode attempt
            val decodedBytes = Base64.decode(input, Base64.DEFAULT)
            String(decodedBytes, Charsets.UTF_8)
        }.getOrNull()
    }
}
