package com.cybervpn.tv.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.cybervpn.tv.ui.theme.NeonCyan

/**
 * Custom Compose Modifier creating a AAA Console-like D-Pad focus interaction.
 * Uses graphicsLayer to bypass expensive measure/layout phases ensuring high frame rates on TV processors.
 */
fun Modifier.tvFocusHighlight(
    shape: Shape = RoundedCornerShape(12.dp),
    focusedGlowColor: Color = NeonCyan
): Modifier =
    composed {
        var isFocused by remember { mutableStateOf(false) }

        val scale by animateFloatAsState(
            targetValue = if (isFocused) 1.05f else 1.0f,
            animationSpec = tween(durationMillis = 200),
            label = "tv_focus_scale"
        )

        val shadowElevation by animateFloatAsState(
            targetValue = if (isFocused) 16f else 0f,
            animationSpec = tween(durationMillis = 200),
            label = "tv_focus_shadow"
        )

        val borderColor by animateColorAsState(
            targetValue = if (isFocused) focusedGlowColor else Color.Transparent,
            animationSpec = tween(durationMillis = 200),
            label = "tv_focus_border"
        )

        this
            .onFocusChanged { isFocused = it.isFocused }
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                this.shadowElevation = shadowElevation
                this.shape = shape
                clip = true
            }
            .border(2.dp, borderColor, shape)
    }
