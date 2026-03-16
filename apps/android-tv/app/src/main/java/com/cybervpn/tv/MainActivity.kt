package com.cybervpn.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.cybervpn.tv.ui.AppNavigation
import com.cybervpn.tv.ui.theme.CyberVpnTvTheme

/**
 * Main Android TV intent entry point configuring the Jetpack Compose TV navigation graph.
 * Pure compose logic replaces legacy XML inflations here.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CyberVpnTvTheme {
                AppNavigation()
            }
        }
    }
}
