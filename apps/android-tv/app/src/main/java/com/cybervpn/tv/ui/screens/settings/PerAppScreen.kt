@file:Suppress("FunctionNaming")

package com.cybervpn.tv.ui.screens.settings

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.tv.foundation.lazy.list.TvLazyColumn
import androidx.tv.foundation.lazy.list.items
import androidx.tv.material3.Checkbox
import androidx.tv.material3.ClickableSurfaceDefaults
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Surface
import androidx.tv.material3.Text
import com.cybervpn.tv.core.state.UiState
import com.google.accompanist.drawablepainter.rememberDrawablePainter

@Composable
fun PerAppScreen(
    modifier: Modifier = Modifier,
    viewModel: PerAppViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Box(modifier = modifier.fillMaxSize()) {
        when (val state = uiState) {
            is UiState.Loading -> {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.Center),
                    color = MaterialTheme.colorScheme.primary
                )
            }
            is UiState.Success -> {
                TvLazyColumn(
                    modifier = Modifier.fillMaxSize()
                ) {
                    item {
                        Text(
                            text = "Split Tunneling (Bypass Apps)",
                            style = MaterialTheme.typography.headlineMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        Text(
                            text = "Selected apps will bypass the VPN entirely.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(bottom = 24.dp)
                        )
                    }

                    items(state.data, key = { it.packageName }) { app ->
                        AppListItem(
                            app = app,
                            onToggle = { bypass ->
                                viewModel.toggleBypass(app.packageName, bypass)
                            }
                        )
                    }
                }
            }
            is UiState.Error -> {
                Text(
                    text = state.message,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.align(Alignment.Center)
                )
            }
        }
    }
}

@Composable
private fun AppListItem(
    app: AppUiModel,
    onToggle: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = { onToggle(!app.isBypassed) },
        colors =
            ClickableSurfaceDefaults.colors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                focusedContainerColor = MaterialTheme.colorScheme.inverseSurface
            ),
        shape =
            ClickableSurfaceDefaults.shape(
                shape = MaterialTheme.shapes.medium
            ),
        modifier =
            modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp)
    ) {
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Image(
                painter = rememberDrawablePainter(drawable = app.icon),
                contentDescription = null,
                modifier = Modifier.size(48.dp)
            )

            Spacer(modifier = Modifier.width(16.dp))

            Text(
                text = app.name,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f)
            )

            Checkbox(
                checked = app.isBypassed,
                onCheckedChange = onToggle
            )
        }
    }
}
