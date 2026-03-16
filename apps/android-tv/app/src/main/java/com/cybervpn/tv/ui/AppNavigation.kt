@file:Suppress("FunctionNaming", "MatchingDeclarationName")

package com.cybervpn.tv.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.tv.material3.DrawerValue
import androidx.tv.material3.Icon
import androidx.tv.material3.NavigationDrawer
import androidx.tv.material3.NavigationDrawerItem
import androidx.tv.material3.Text
import androidx.tv.material3.rememberDrawerState
import com.cybervpn.tv.ui.screens.dashboard.DashboardScreen
import com.cybervpn.tv.ui.screens.profiles.ProfilesScreen
import com.cybervpn.tv.ui.screens.settings.SettingsScreen

enum class TvRoute(val title: String, val icon: ImageVector) {
    Dashboard("Dashboard", Icons.Default.Home),
    Profiles("Profiles", Icons.Default.List),
    Settings("Settings", Icons.Default.Settings),
}

@Composable
fun AppNavigation(
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
) {
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    var currentRoute by remember { mutableStateOf(TvRoute.Dashboard) }

    NavigationDrawer(
        modifier = modifier,
        drawerState = drawerState,
        drawerContent = { _ ->
            Column(
                Modifier
                    .fillMaxHeight()
                    .padding(12.dp),
            ) {
                TvRoute.values().forEach { route ->
                    NavigationDrawerItem(
                        selected = currentRoute == route,
                        onClick = {
                            currentRoute = route
                            navController.navigate(route.name) {
                                // Pop up to start to avoid stack buildup in TV D-pad flows
                                popUpTo(TvRoute.Dashboard.name)
                                launchSingleTop = true
                            }
                        },
                        leadingContent = {
                            Icon(
                                imageVector = route.icon,
                                contentDescription = route.title,
                            )
                        },
                    ) {
                        Text(text = route.title)
                    }
                }
            }
        },
    ) {
        NavHost(
            navController = navController,
            startDestination = TvRoute.Dashboard.name,
        ) {
            composable(TvRoute.Dashboard.name) {
                DashboardScreen()
            }
            composable(TvRoute.Profiles.name) {
                ProfilesScreen()
            }
            composable(TvRoute.Settings.name) {
                SettingsScreen()
            }
        }
    }
}
