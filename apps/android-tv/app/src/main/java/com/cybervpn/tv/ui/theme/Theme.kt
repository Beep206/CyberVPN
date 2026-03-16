@file:Suppress("FunctionNaming", "MagicNumber")

package com.cybervpn.tv.ui.theme

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.darkColorScheme

private val CyberpunkColorScheme =
    darkColorScheme(
        primary = NeonCyan,
        onPrimary = DarkBackground,
        primaryContainer = MatrixGreen,
        onPrimaryContainer = DarkBackground,
        secondary = NeonPink,
        onSecondary = Color.White,
        background = DarkBackground,
        onBackground = CypherTextPrimary,
        surface = DarkSurface,
        onSurface = CypherTextPrimary,
        surfaceVariant = DarkSurfaceVariant,
        onSurfaceVariant = CypherTextSecondary,
        error = ErrorRed,
        onError = Color.White,
    )

/**
 * Animated subtle background to prevent OLED burn-in on Android TVs.
 * Constantly slowly pulses and shifts dark tones so that pixels do not sit
 * statically on completely black/dark for hours.
 */
@Composable
fun AntiBurnInBackground(modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition(label = "burn_in_prevention")
    // Animate between two slightly different dark tones
    val shiftX by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec =
            infiniteRepeatable(
                animation = tween(durationMillis = 20000, easing = LinearEasing),
                repeatMode = RepeatMode.Reverse,
            ),
        label = "shift_x",
    )

    val shiftY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec =
            infiniteRepeatable(
                animation = tween(durationMillis = 25000, easing = LinearEasing),
                repeatMode = RepeatMode.Reverse,
            ),
        label = "shift_y",
    )

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(
                    brush =
                        Brush.radialGradient(
                            colors =
                                listOf(
                                    DarkBackground,
                                    Color(0xFF030308),
                                    Color(0xFF010103),
                                ),
                            center = Offset(shiftX, shiftY),
                            radius = 2000f,
                        ),
                ),
    )
}

/**
 * The main Jetpack Compose theme wrapper specifically adhering to [androidx.tv.material3] specs.
 */
@Composable
fun CyberVpnTvTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = CyberpunkColorScheme,
    ) {
        // Enforce the Anti-Burn-In Background underneath all content
        Box(modifier = Modifier.fillMaxSize()) {
            AntiBurnInBackground()
            content()
        }
    }
}
