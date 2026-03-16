@file:Suppress("FunctionNaming", "LongMethod", "MagicNumber")

package com.cybervpn.tv.ui.screens.profiles

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.tv.material3.ClickableSurfaceDefaults
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Surface
import androidx.tv.material3.Text
import com.cybervpn.tv.ui.components.tvFocusHighlight
import com.cybervpn.tv.ui.theme.MatrixGreen
import com.cybervpn.tv.ui.theme.NeonCyan

@Composable
fun ProfilesScreen(
    modifier: Modifier = Modifier,
    viewModel: ImportViewModel = hiltViewModel()
) {
    var showDialog by remember { mutableStateOf(false) }
    val ipAddress by viewModel.ipAddress.collectAsStateWithLifecycle()
    val pairingCode by viewModel.pairingCode.collectAsStateWithLifecycle()

    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Surface(
                onClick = { showDialog = true },
                modifier =
                    Modifier
                        .size(300.dp, 80.dp)
                        .tvFocusHighlight(shape = RoundedCornerShape(12.dp)),
                shape =
                    ClickableSurfaceDefaults.shape(
                        shape = RoundedCornerShape(12.dp)
                    )
            ) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "IMPORT FROM PHONE",
                        style = MaterialTheme.typography.titleMedium,
                        color = NeonCyan
                    )
                }
            }
        }

        if (showDialog) {
            Dialog(onDismissRequest = { showDialog = false }) {
                Surface(
                    shape = ClickableSurfaceDefaults.shape(shape = RoundedCornerShape(16.dp)),
                    colors = ClickableSurfaceDefaults.colors(containerColor = Color(0xFF111111))
                ) {
                    Column(
                        modifier = Modifier.padding(32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "DEVICE PAIRING",
                            style = MaterialTheme.typography.headlineMedium,
                            color = NeonCyan
                        )
                        Spacer(modifier = Modifier.height(24.dp))
                        Text(text = "Navigate to this address on your phone:", color = Color.White)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "http://$ipAddress:8080",
                            style = MaterialTheme.typography.titleLarge,
                            color = MatrixGreen
                        )
                        Spacer(modifier = Modifier.height(24.dp))
                        Text(text = "Security Code:", color = Color.White)
                        Text(
                            text = "$pairingCode",
                            style = MaterialTheme.typography.headlineSmall,
                            color = NeonCyan
                        )

                        Spacer(modifier = Modifier.height(32.dp))
                        Row {
                            Surface(
                                onClick = { showDialog = false },
                                modifier = Modifier.tvFocusHighlight(shape = RoundedCornerShape(8.dp))
                            ) {
                                Box(modifier = Modifier.padding(horizontal = 24.dp, vertical = 12.dp)) {
                                    Text(text = "CLOSE")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
