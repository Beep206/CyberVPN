package com.cybervpn.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.cybervpn.tv.core.tv.TvChannelManager
import com.cybervpn.tv.ui.AppNavigation
import com.cybervpn.tv.ui.theme.CyberVpnTvTheme
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

/**
 * Main Android TV intent entry point configuring the Jetpack Compose TV navigation graph.
 * Pure compose logic replaces legacy XML inflations here.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var tvChannelManager: TvChannelManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        tvChannelManager.initializePlayNext()

        setContent {
            CyberVpnTvTheme {
                AppNavigation()
            }
        }
    }
}
