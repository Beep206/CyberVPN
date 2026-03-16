@file:Suppress("FunctionNaming")

package com.cybervpn.tv.ui.screens.dashboard

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.tv.material3.ClickableSurfaceDefaults
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Surface
import androidx.tv.material3.Text
import com.cybervpn.tv.core.state.ConnectionState
import com.cybervpn.tv.core.state.UiState
import com.cybervpn.tv.ui.components.tvFocusHighlight
import com.cybervpn.tv.ui.theme.ErrorRed
import com.cybervpn.tv.ui.theme.MatrixGreen
import com.cybervpn.tv.ui.theme.NeonCyan

@Composable
fun DashboardScreen(
    modifier: Modifier = Modifier,
    viewModel: VpnViewModel = hiltViewModel()
) {
    val connectionState by viewModel.connectionState.collectAsStateWithLifecycle()

    val stateText =
        when (val state = connectionState) {
            is UiState.Success -> state.data.name
            is UiState.Loading -> "LOADING"
            is UiState.Error -> "ERROR"
        }

    val glowColor =
        when (val state = connectionState) {
            is UiState.Success -> {
                if (state.data == ConnectionState.CONNECTED) MatrixGreen else NeonCyan
            }
            is UiState.Error -> ErrorRed
            else -> NeonCyan
        }

    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Surface(
                onClick = { viewModel.toggleConnection() },
                modifier =
                    Modifier
                        .size(200.dp)
                        .tvFocusHighlight(shape = CircleShape, focusedGlowColor = glowColor),
                shape =
                    ClickableSurfaceDefaults.shape(
                        shape = CircleShape
                    )
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    val isConnected = (connectionState as? UiState.Success)?.data == ConnectionState.CONNECTED
                    Text(
                        text = if (isConnected) "DISCONNECT" else "CONNECT",
                        style = MaterialTheme.typography.titleLarge
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            Text(
                text = "STATUS: $stateText",
                style = MaterialTheme.typography.bodyLarge,
                color = glowColor
            )

            Spacer(modifier = Modifier.height(16.dp))

            Text(text = "Current IP: 192.168.1.1 (Mock)")
            Text(text = "Ping: 42ms | Up: 120Mbps | Down: 350Mbps")
        }
    }
}
