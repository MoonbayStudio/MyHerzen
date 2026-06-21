package ru.moonbaystudio.myherzen.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import ru.moonbaystudio.myherzen.data.repository.ScheduleRepository
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val userPreferences: UserPreferences,
    private val repository: ScheduleRepository
) : ViewModel() {
    val defaultPersona = userPreferences.defaultPersona.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), "pelikasha")
    val selectedGroupName = userPreferences.selectedGroupName.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)
    val selectedThemeId = userPreferences.selectedThemeId.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), "classic")
    val scheduleCacheWeeks = userPreferences.scheduleCacheWeeks.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 2)
    val liveActivityEnabled = userPreferences.liveActivityEnabled.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), true)

    fun updateDefaultPersona(persona: String) = viewModelScope.launch {
        userPreferences.updateDefaultPersona(persona)
    }

    fun updateTheme(themeId: String) = viewModelScope.launch {
        userPreferences.saveThemeId(themeId)
    }

    fun updateScheduleCacheWeeks(weeks: Int) = viewModelScope.launch {
        userPreferences.updateScheduleCacheWeeks(weeks)
    }

    fun updateLiveActivityEnabled(enabled: Boolean) = viewModelScope.launch {
        userPreferences.updateLiveActivityEnabled(enabled)
    }

    fun clearCache() {
        viewModelScope.launch {
            userPreferences.selectedGroupId.first()?.let { groupId ->
                repository.clearCache(groupId)
            }
        }
    }
}
