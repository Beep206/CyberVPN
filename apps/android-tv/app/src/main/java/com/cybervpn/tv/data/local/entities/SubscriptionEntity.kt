package com.cybervpn.tv.data.local.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "subscriptions")
data class SubscriptionEntity(
    @PrimaryKey
    val id: String,
    val name: String,
    val url: String,
    val lastUpdated: Long,
)
