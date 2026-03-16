package com.cybervpn.tv.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "bypass_packages")

@Singleton
class RoutingRepository @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val bypassedPackagesKey = stringSetPreferencesKey("bypassed_packages")

    val bypassedPackages: Flow<Set<String>> =
        context.dataStore.data.map { preferences ->
            preferences[bypassedPackagesKey] ?: emptySet()
        }

    suspend fun togglePackageBypass(
        packageName: String,
        bypass: Boolean
    ) {
        context.dataStore.edit { preferences ->
            val currentSet = preferences[bypassedPackagesKey] ?: emptySet()
            val newSet = currentSet.toMutableSet()

            if (bypass) {
                newSet.add(packageName)
            } else {
                newSet.remove(packageName)
            }

            preferences[bypassedPackagesKey] = newSet
        }
    }
}
