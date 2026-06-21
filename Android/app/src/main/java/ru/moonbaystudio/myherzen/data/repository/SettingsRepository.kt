package ru.moonbaystudio.myherzen.data.repository

import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepository @Inject constructor(
    private val userPreferences: UserPreferences
) {
    val selectedGroupId = userPreferences.selectedGroupId
    val selectedGroupName = userPreferences.selectedGroupName
    val scheduleCacheWeeks = userPreferences.scheduleCacheWeeks
    val offlineScheduleEnabled = userPreferences.liveActivityEnabled // Assuming this maps to it
    val offlineScheduleWeeks = userPreferences.scheduleCacheWeeks
    val liveActivityEnabled = userPreferences.liveActivityEnabled

    suspend fun saveSelectedGroup(id: Int, name: String) {
        userPreferences.saveSelectedGroup(id, name)
    }

    suspend fun updateScheduleCacheWeeks(weeks: Int) {
        userPreferences.updateScheduleCacheWeeks(weeks)
    }

    suspend fun updateLiveActivityEnabled(enabled: Boolean) {
        userPreferences.updateLiveActivityEnabled(enabled)
    }
}
