package com.cybervpn.tv.ui.screens.dashboard

import androidx.lifecycle.ViewModel
import com.cybervpn.tv.core.state.ConnectionState
import com.cybervpn.tv.core.state.UiState
import com.cybervpn.tv.data.repository.VpnRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class VpnViewModel @Inject constructor(
    private val repository: VpnRepository
) : ViewModel() {

    val connectionState: StateFlow<UiState<ConnectionState>> = repository.connectionState

    fun toggleConnection() {
        val current = connectionState.value
        if (current is UiState.Success) {
            val newState =
                if (current.data == ConnectionState.CONNECTED) {
                    ConnectionState.DISCONNECTED
                } else {
                    ConnectionState.CONNECTED
                }
            repository.updateConnectionState(newState)
        }
    }
}
