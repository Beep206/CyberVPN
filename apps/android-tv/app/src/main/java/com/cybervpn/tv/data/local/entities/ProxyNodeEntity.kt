package com.cybervpn.tv.data.local.entities

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import com.cybervpn.tv.core.model.ProxyNode
import com.cybervpn.tv.core.model.VpnProtocol

@Entity(
    tableName = "proxy_nodes",
    foreignKeys = [
        ForeignKey(
            entity = SubscriptionEntity::class,
            parentColumns = ["id"],
            childColumns = ["subscriptionId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("subscriptionId")],
)
data class ProxyNodeEntity(
    @PrimaryKey
    val id: String,
    val subscriptionId: String,
    val name: String,
    val protocol: String,
    val server: String,
    val port: Int,
    val uuid: String?,
    val password: String?,
    val method: String?,
    val tls: String?,
    val sni: String?,
    val fingerprint: String?,
    val alpn: String?,
    val pbk: String?,
    val sid: String?,
    val network: String?,
    val path: String?,
    val host: String?,
    val upMbps: Int?,
    val downMbps: Int?,
    val obfs: String?,
    val obfsPassword: String?,
)

@Suppress("TooGenericExceptionCaught", "SwallowedException")
fun ProxyNodeEntity.toDomainModel() =
    ProxyNode(
        id = id,
        name = name,
        protocol =
            try {
                VpnProtocol.valueOf(protocol)
            } catch (e: Exception) {
                VpnProtocol.UNKNOWN
            },
        server = server,
        port = port,
        uuid = uuid,
        password = password,
        method = method,
        tls = tls,
        sni = sni,
        fingerprint = fingerprint,
        alpn = alpn,
        pbk = pbk,
        sid = sid,
        network = network,
        path = path,
        host = host,
        upMbps = upMbps,
        downMbps = downMbps,
        obfs = obfs,
        obfsPassword = obfsPassword,
    )

fun ProxyNode.toEntity(subId: String) =
    ProxyNodeEntity(
        id = id,
        subscriptionId = subId,
        name = name,
        protocol = protocol.name,
        server = server,
        port = port,
        uuid = uuid,
        password = password,
        method = method,
        tls = tls,
        sni = sni,
        fingerprint = fingerprint,
        alpn = alpn,
        pbk = pbk,
        sid = sid,
        network = network,
        path = path,
        host = host,
        upMbps = upMbps,
        downMbps = downMbps,
        obfs = obfs,
        obfsPassword = obfsPassword,
    )
