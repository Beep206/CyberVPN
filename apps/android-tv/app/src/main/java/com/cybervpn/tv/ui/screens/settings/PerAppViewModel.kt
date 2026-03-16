package com.cybervpn.tv.ui.screens.settings

import android.graphics.drawable.Drawable
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cybervpn.tv.core.state.UiState
import com.cybervpn.tv.core.system.AppManager
import com.cybervpn.tv.data.RoutingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AppUiModel(
    val packageName: String,
    val name: String,
    val icon: Drawable,
    val isBypassed: Boolean
)

@HiltViewModel
class PerAppViewModel @Inject constructor(
    private val appManager: AppManager,
    private val routingRepository: RoutingRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<List<AppUiModel>>>(UiState.Loading)
    val uiState: StateFlow<UiState<List<AppUiModel>>> = _uiState.asStateFlow()

    init {
        loadApps()
    }

    private fun loadApps() {
        viewModelScope.launch {
            val installedAppsFlow =
                kotlinx.coroutines.flow.flow {
                    emit(appManager.getInstalledApps())
                }

            installedAppsFlow.combine(routingRepository.bypassedPackages) { apps, bypassedSet ->
                val models =
                    apps.map { app ->
                        AppUiModel(
                            packageName = app.packageName,
                            name = app.name,
                            icon = app.icon,
                            isBypassed = bypassedSet.contains(app.packageName)
                        )
                    }
                UiState.Success(models)
            }.launchIn(viewModelScope)
        }
    }

    fun toggleBypass(
        packageName: String,
        bypass: Boolean
    ) {
        viewModelScope.launch {
            routingRepository.togglePackageBypass(packageName, bypass)
        }
    }
}
