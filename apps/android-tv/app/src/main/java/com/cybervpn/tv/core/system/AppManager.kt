package com.cybervpn.tv.core.system

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import com.cybervpn.tv.core.model.TvApp
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AppManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    suspend fun getInstalledApps(): List<TvApp> =
        withContext(Dispatchers.IO) {
            val packageManager = context.packageManager
            val allPackages = packageManager.getInstalledPackages(PackageManager.GET_META_DATA)

            allPackages.mapNotNull { packageInfo ->
                val appInfo = packageInfo.applicationInfo ?: return@mapNotNull null

                // Filter out system apps that the user generally wouldn't interact with
                val isSystemApp = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                if (isSystemApp) return@mapNotNull null

                val packageName = packageInfo.packageName
                val name = appInfo.loadLabel(packageManager).toString()
                val icon = appInfo.loadIcon(packageManager)

                TvApp(
                    packageName = packageName,
                    name = name,
                    icon = icon
                )
            }.sortedBy { it.name }
        }
}
