package com.cybervpn.tv.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import com.cybervpn.tv.data.local.entities.ProxyNodeEntity
import com.cybervpn.tv.data.local.entities.SubscriptionEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface VpnDao {
    @Query("SELECT * FROM subscriptions")
    fun getAllSubscriptions(): Flow<List<SubscriptionEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSubscription(subscription: SubscriptionEntity)

    @Query("DELETE FROM subscriptions WHERE id = :subId")
    suspend fun deleteSubscription(subId: String)

    @Query("SELECT * FROM proxy_nodes WHERE subscriptionId = :subId")
    fun getNodesBySubscription(subId: String): Flow<List<ProxyNodeEntity>>

    @Query("SELECT * FROM proxy_nodes")
    fun getAllNodes(): Flow<List<ProxyNodeEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNodes(nodes: List<ProxyNodeEntity>)

    @Query("DELETE FROM proxy_nodes WHERE subscriptionId = :subId")
    suspend fun deleteNodesBySubscription(subId: String)

    @Transaction
    suspend fun syncNodesForSubscription(
        subId: String,
        nodes: List<ProxyNodeEntity>,
    ) {
        deleteNodesBySubscription(subId)
        insertNodes(nodes)
    }
}
