package com.cybervpn.tv.data.repository

import com.cybervpn.tv.core.model.ProxyNode
import com.cybervpn.tv.core.network.SubscriptionClient
import com.cybervpn.tv.core.state.ConnectionState
import com.cybervpn.tv.core.state.UiState
import com.cybervpn.tv.data.local.dao.VpnDao
import com.cybervpn.tv.data.local.entities.SubscriptionEntity
import com.cybervpn.tv.data.local.entities.toDomainModel
import com.cybervpn.tv.data.local.entities.toEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class VpnRepository
    @Inject
    constructor(
        private val vpnDao: VpnDao,
        private val subscriptionClient: SubscriptionClient,
    ) {
        private val _connectionState =
            MutableStateFlow<UiState<ConnectionState>>(
                UiState.Success(ConnectionState.DISCONNECTED),
            )
        val connectionState: StateFlow<UiState<ConnectionState>> = _connectionState.asStateFlow()

        val allSubscriptions: Flow<List<SubscriptionEntity>> = vpnDao.getAllSubscriptions()

        val allNodes: Flow<List<ProxyNode>> =
            vpnDao.getAllNodes().map { entities ->
                withContext(Dispatchers.Default) {
                    entities.map { it.toDomainModel() }
                }
            }

        @Suppress("TooGenericExceptionCaught")
        suspend fun syncSubscription(sub: SubscriptionEntity): UiState<Unit> {
            return try {
                val fetchedNodes = subscriptionClient.fetchSubscription(sub.url)
                if (fetchedNodes == null) {
                    UiState.Error("Failed to fetch subscription nodes.")
                } else {
                    withContext(Dispatchers.Default) {
                        val entities = fetchedNodes.map { it.toEntity(sub.id) }
                        vpnDao.syncNodesForSubscription(sub.id, entities)
                    }
                    UiState.Success(Unit)
                }
            } catch (e: Exception) {
                UiState.Error(e.message ?: "Unknown error during sync", e)
            }
        }

        suspend fun addSubscription(sub: SubscriptionEntity) {
            vpnDao.insertSubscription(sub)
        }

        suspend fun removeSubscription(subId: String) {
            vpnDao.deleteSubscription(subId)
        }

        fun updateConnectionState(state: ConnectionState) {
            _connectionState.value = UiState.Success(state)
        }
    }
