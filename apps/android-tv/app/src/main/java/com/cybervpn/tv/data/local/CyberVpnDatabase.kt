package com.cybervpn.tv.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.cybervpn.tv.data.local.dao.VpnDao
import com.cybervpn.tv.data.local.entities.ProxyNodeEntity
import com.cybervpn.tv.data.local.entities.SubscriptionEntity

@Database(
    entities = [
        SubscriptionEntity::class,
        ProxyNodeEntity::class,
    ],
    version = 1,
    exportSchema = false,
)
abstract class CyberVpnDatabase : RoomDatabase() {
    abstract val vpnDao: VpnDao
}
