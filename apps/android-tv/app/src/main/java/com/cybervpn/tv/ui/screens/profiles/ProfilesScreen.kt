@file:Suppress("FunctionNaming")

package com.cybervpn.tv.ui.screens.profiles

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.tv.material3.ClickableSurfaceDefaults
import androidx.tv.material3.Surface
import androidx.tv.material3.Text
import com.cybervpn.tv.ui.components.tvFocusHighlight

@Composable
fun ProfilesScreen(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            onClick = { /* TODO */ },
            modifier =
                Modifier
                    .size(200.dp, 100.dp)
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
                Text(text = "Mock Profile")
            }
        }
    }
}
